import gc
import json
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime

import psutil
import RPi.GPIO as GPIO

import sensors

# Setup button input pins for different sensors
array_mic_button = 26  # Respeaker series


# set a global name for a common logging for functions using this module
LOG = "multi-channel-rpi-eco-monitoring"


def is_internet_available():
    """
    Check if internet is available by connecting to a public DNS.
    Using a more robust timeout.
    """
    try:
        # Increased timeout to 10 seconds to be more robust
        socket.create_connection(("8.8.8.8", 53), timeout=10)
        return True
    except OSError:
        return False


def auto_update_repository():
    """
    Force-sync repository to origin/master, discarding local changes.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logging.info("Memulai auto-update repository...")

        # 1. Ensure we are on the master branch
        subprocess.call(["git", "-C", script_dir, "checkout", "master"], timeout=30)

        # 2. Fetch latest data from remote
        subprocess.call(["git", "-C", script_dir, "fetch", "origin"], timeout=30)

        # 3. FORCE RESET to origin/master (THIS WILL DISCARD ALL LOCAL CHANGES ON THE RPI)
        subprocess.call(
            ["git", "-C", script_dir, "reset", "--hard", "origin/master"], timeout=60
        )

        # 4. Clean up unnecessary files
        subprocess.call(
            [
                "git",
                "-C",
                script_dir,
                "clean",
                "-fd",
                "-e",
                "config.json",
                "-e",
                "logs/",
            ],
            timeout=30,
        )

        logging.info("Auto-update complete.")
    except Exception as e:
        logging.warning("Auto-update failed: {}".format(e))


def gc_and_log_memory(caller_name):
    """
    Run garbage collection to reclaim memory and log current Python process
    and overall system RAM usage to diagnose and prevent memory leaks.
    """
    try:
        # Run Garbage Collector
        collected = gc.collect()

        # Get process memory usage
        process = psutil.Process(os.getpid())
        proc_mem_mb = process.memory_info().rss / (1024 * 1024)

        # Get overall system memory usage
        sys_mem = psutil.virtual_memory()
        sys_avail_mb = sys_mem.available / (1024 * 1024)
        sys_total_mb = sys_mem.total / (1024 * 1024)

        logging.info(
            "RAM: {:.0f} MB proc, {:.0f}/{:.0f} MB free/total, {} objects freed.".format(
                proc_mem_mb, sys_avail_mb, sys_total_mb, collected
            )
        )
    except Exception as e:
        logging.warning(
            "Failed to collect garbage or log memory in {}: {}".format(caller_name, e)
        )


class MinuteBoundaryFormatter(logging.Formatter):
    """
    Prefix log message with timestamp only when the minute changes.
    """

    def __init__(self):
        super().__init__("%(message)s")
        self._last_minute = None
        self._lock = threading.Lock()

    def format(self, record):
        msg = super().format(record)
        minute_stamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M")

        with self._lock:
            if minute_stamp != self._last_minute:
                self._last_minute = minute_stamp
                return "[{}] {}".format(minute_stamp, msg)

        return msg


"""
Running the recording process uses the following functions, which users
might want to repackage in bespoke code, or which it is useful to isolate
for testing:

Sensor setup and recording
* configure_sensor(config_file) # returns a configured sensor
* record_sensor(sensor, wdir, udir, sensor_config, sleep=True) # initiates a single round of sampling

FTP server sync
* upload_server_sync(rclone_config, udir) # rolling synchronisation, intended to run in thread

Utility
* clean_dirs(wdir, udir) # cleans out trash in wdir and udir
"""


def safe_shutdown():
    """
    Safely powers down the device (without corruption)
    ...even when threads are running (it will halt these first)
    -h stands for 'halt'
    """
    # Flush buffered log records before halting so final warnings are persisted.
    try:
        for handler in logging.getLogger().handlers:
            handler.flush()
    except Exception:
        pass
    logging.shutdown()

    shutdown_cmd = "sudo shutdown -h now"
    subprocess.call(shutdown_cmd, shell=True)


def parse_reboot_times(sys_config):
    """
    Parse configured daily reboot times from legacy and new config keys.

    Supported formats:
    - sys.reboot_time: "HH:MM"
    - sys.reboot_time_2: "HH:MM"
    - sys.reboot_times: ["HH:MM", "HH:MM"] or "HH:MM,HH:MM"
    """
    reboot_candidates = []

    reboot_time = sys_config.get("reboot_time")
    if reboot_time:
        reboot_candidates.append(reboot_time)

    reboot_time_2 = sys_config.get("reboot_time_2")
    if reboot_time_2:
        reboot_candidates.append(reboot_time_2)

    reboot_times = sys_config.get("reboot_times", [])
    if isinstance(reboot_times, str):
        reboot_candidates.extend(
            [value.strip() for value in reboot_times.split(",") if value.strip()]
        )
    elif isinstance(reboot_times, list):
        reboot_candidates.extend(reboot_times)

    validated_times = []
    seen_times = set()
    for candidate in reboot_candidates:
        if not candidate:
            continue
        try:
            normalized_time = datetime.strptime(
                str(candidate).strip(), "%H:%M"
            ).strftime("%H:%M")
        except ValueError:
            logging.warning("Ignoring invalid reboot time: {}".format(candidate))
            continue

        if normalized_time not in seen_times:
            seen_times.add(normalized_time)
            validated_times.append(normalized_time)

    return sorted(validated_times)


def scheduled_reboot_monitor(reboot_times, die, recording_in_progress=None):
    """
    Monitor local time and trigger a reboot when a configured reboot time is reached.
    """
    last_trigger = None
    pending_reboot = None

    while not die.is_set():
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        trigger_key = now.strftime("%Y-%m-%d %H:%M")

        if current_time in reboot_times and trigger_key != last_trigger:
            last_trigger = trigger_key
            pending_reboot = current_time
            logging.warning("Scheduled reboot requested for {}".format(current_time))

        if pending_reboot is not None:
            if recording_in_progress is not None and recording_in_progress.is_set():
                logging.info(
                    "Deferring scheduled reboot {} until current recording completes".format(
                        pending_reboot
                    )
                )
            else:
                logging.warning(
                    "Scheduled reboot triggered for {}".format(pending_reboot)
                )
                subprocess.call("sudo reboot", shell=True)

        die.wait(20)


def configure_sensor(sensor_config):
    """
    Get a sensor from the sensor config settings
    Args:
        sensor_config: Path to the sensor configuration file
    Returns:
        An instance of a sensor class.
    """

    # Get a reference to the Sensor class
    sensor_type = sensor_config["sensor_type"]
    try:
        sensor_class = getattr(sensors, sensor_type)
        logging.info("Sensor type {} being configured.".format(sensor_type))
    except AttributeError:
        logging.critical("Sensor type {} not found.".format(sensor_type))
        sys.exit()

    # get a configured instance of the sensor
    # TODO - not sure of exception classes here?
    try:
        sensor = sensor_class(sensor_config)
        logging.info("{} Sensor config succeeded.".format(sensor_type))
    except ValueError as e:
        logging.critical("{} Sensor config failed.".format(sensor_type))
        raise e

    # If it passes config, does it pass setup.
    if sensor.setup():
        logging.info("Sensor setup succeeded")
    else:
        logging.critical("Sensor setup failed.")
        sys.exit()

    return sensor


def check_last_recording_size(upload_dir, pre_upload_dir=None):
    """
    Check the latest recording artefact across upload/pre-upload directories.
    Returns True when the latest artefact indicates a failed or suspiciously small
    recording.
    """
    try:
        scan_roots = [upload_dir]
        if pre_upload_dir:
            scan_roots.append(pre_upload_dir)

        candidates = []
        for scan_root in scan_roots:
            if not scan_root or (not os.path.isdir(scan_root)):
                continue
            for root, dirs, files in os.walk(scan_root):
                for file in files:
                    full_path = os.path.join(root, file)
                    file_lower = file.lower()
                    if file_lower.endswith((".wav", ".flac", ".mp3")):
                        candidates.append(
                            {
                                "path": full_path,
                                "mtime": os.path.getmtime(full_path),
                                "kind": "audio",
                                "size": os.path.getsize(full_path),
                            }
                        )
                    elif "_error_audio-record-failed" in file_lower:
                        candidates.append(
                            {
                                "path": full_path,
                                "mtime": os.path.getmtime(full_path),
                                "kind": "error",
                                "size": 0,
                            }
                        )

        if not candidates:
            logging.info("No recording artefacts found for size check.")
            return False

        latest = max(candidates, key=lambda c: c["mtime"])
        latest_file = latest["path"]

        if latest["kind"] == "error":
            logging.warning(
                "Latest recording artefact is an error marker: {}".format(latest_file)
            )
            return True

        file_size = latest["size"]
        if file_size < 1048576:  # 1 MB in bytes
            logging.warning(
                "Last recording file {} is too small ({} bytes < 1 MB).".format(
                    latest_file, file_size
                )
            )
            return True
        else:
            logging.info(
                "Last recording file {} size is {} bytes, OK.".format(
                    latest_file, file_size
                )
            )
            return False
    except Exception as e:
        logging.error("Error checking recording file size: {}".format(e))
        return False


def record_sensor(sensor, working_dir, upload_dir, sensor_config, sleep=True):
    """
    Function to run the common sensor record loop. The sleep between
    sensor recordings can be turned off
    Args:
        sensor: A sensor instance
        working_dir: The working directory to be used by the sensor
        upload_dir: The upload directory root to use for completed files
        sensor_config: The sensor configuration dictionary
        sleep: Boolean - should the sensor sleep be used.
    """

    # Create daily folders to hold files during this recording session
    start_date = time.strftime("%Y-%m-%d")
    session_working_dir = os.path.join(working_dir, start_date)
    session_upload_dir = os.path.join(upload_dir, start_date)
    # TODO pre_upload dir as a config variable
    session_pre_upload_dir = os.path.join("/home/pi/pre_upload_dir", start_date)

    try:
        if not os.path.exists(session_working_dir):
            os.makedirs(session_working_dir)
    except OSError:
        logging.critical(
            "Could not create working directory for recording: {}".format(
                session_working_dir
            )
        )
        sys.exit()

    try:
        if not os.path.exists(session_upload_dir):
            os.makedirs(session_upload_dir)
    except OSError:
        logging.critical(
            "Could not create upload directory for recording: {}".format(
                session_upload_dir
            )
        )
        sys.exit()

    # Create the Pre-Upload Directory (For Storing all Finished Recordings)
    try:
        if not os.path.exists(session_pre_upload_dir):
            os.makedirs(session_pre_upload_dir)
    except OSError:
        logging.critical(
            "Could not create pre-upload directory for recording: {}".format(
                session_pre_upload_dir
            )
        )
        logging.critical("continuing anyway...")
        # sys.exit()

    # Capture data from the sensor
    start_capture = time.time()
    logging.info("Capture started.")
    try:
        sensor.capture_data(
            working_dir=session_working_dir,
            upload_dir=session_upload_dir,
            pre_upload_dir=session_pre_upload_dir,
        )
        elapsed = time.time() - start_capture
        logging.info("Capture completed in {:.1f}s.".format(elapsed))
    except Exception:
        elapsed = time.time() - start_capture
        logging.error(
            "record_sensor: capture_data raised an exception after {:.1f}s for {}. "
            "Check sensor class stderr logs above.".format(elapsed, start_date)
        )
        # Re-raise so continuous_recording loop catches and counts tiny file streak.
        raise

    # Let the sensor sleep
    if sleep:
        sensor.sleep()


def _is_wav_file(path):
    """Return True if path begins with a RIFF/WAVE header (valid WAV magic bytes)."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        return len(header) == 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    except OSError:
        return False


def run_postprocess(sensor, upload_dir):
    """
    Function to handle mandatory postprocessing (move, convert, compress)
    of recordings before the next recording cycle starts.

    Steps:
      1. Recursively scan tmp_dir for files to stage into pre_upload_dir:
         - Files ending in .wav are moved as-is.
         - Files with no extension are validated via WAV magic bytes; valid
           ones are renamed to <name>.wav before moving. Invalid or too-small
           files are discarded.
      2. Recursively scan pre_upload_dir for all .wav files.
      3. For each WAV: discard if < MIN_VALID_BYTES, otherwise call
         sensor.postprocess(). If postprocess returns False (compression
         failed) discard the WAV rather than leaving it to block future runs.
    """
    MIN_VALID_BYTES = 1024 * 1024  # 1 MB
    tmp_dir = "/home/pi/tmp_dir"
    pre_upload_dir = "/home/pi/pre_upload_dir"

    # 1. Recursively scan tmp_dir and stage files into pre_upload_dir.
    for root, _, files in os.walk(tmp_dir):
        for name in files:
            src = os.path.join(root, name)
            rel = os.path.relpath(root, tmp_dir)
            dst_dir = os.path.join(pre_upload_dir, rel)

            if name.lower().endswith(".wav"):
                # Already has the correct extension — move as-is.
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src, os.path.join(dst_dir, name))
                logging.info("Staged {} -> pre-upload ({})".format(name, rel))

            elif "." not in name:
                # No extension: likely an arecord output interrupted before
                # capture_data could rename it. Validate before accepting.
                try:
                    size = os.path.getsize(src)
                except OSError:
                    logging.warning("Could not stat {}; skipping.".format(src))
                    continue

                if size < MIN_VALID_BYTES:
                    logging.warning(
                        "Raw file too small ({:.1f} KB < 1 MB), discarding: {}".format(
                            size / 1024.0, name
                        )
                    )
                    try:
                        os.remove(src)
                    except OSError as exc:
                        logging.error("Could not delete {}: {}".format(src, exc))
                    continue

                if not _is_wav_file(src):
                    logging.warning(
                        "Not a WAV file (no RIFF/WAVE header), discarding: {}".format(
                            name
                        )
                    )
                    try:
                        os.remove(src)
                    except OSError as exc:
                        logging.error("Could not delete {}: {}".format(src, exc))
                    continue

                wav_name = name + ".wav"
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src, os.path.join(dst_dir, wav_name))
                logging.info(
                    "Raw WAV found (no ext): {} -> staged as {}".format(name, wav_name)
                )
            # Files with other extensions are left untouched.

    # 2. Collect all WAV files now in pre_upload_dir.
    file_list = []
    for root, _, files in os.walk(pre_upload_dir):
        for name in files:
            if name.lower().endswith(".wav"):
                file_list.append(os.path.join(root, name))

    if not file_list:
        return

    logging.info("Processing {} files...".format(len(file_list)))
    for wav_path in file_list:
        # 3a. Discard files that are too small to be valid recordings.
        try:
            size = os.path.getsize(wav_path)
        except OSError:
            logging.warning("Could not stat {}; skipping.".format(wav_path))
            continue

        if size < MIN_VALID_BYTES:
            logging.warning(
                "Discarding too-small file ({:.1f} KB < 1 MB): {}".format(
                    size / 1024.0, os.path.basename(wav_path)
                )
            )
            try:
                os.remove(wav_path)
            except OSError as exc:
                logging.error("Could not delete {}: {}".format(wav_path, exc))
            continue

        # 3b. Attempt compression / staging.
        ok = sensor.postprocess(wav_path, upload_dir)
        if not ok and os.path.exists(wav_path):
            logging.warning(
                "Compression failed or interrupted; keeping source WAV to retry later: {}".format(
                    os.path.basename(wav_path)
                )
            )


def exit_handler(signal, frame):
    """
    Function to allow the thread loops to be shut down
    :param signal:
    :param frame:
    :return:
    """

    logging.info("SIGINT detected, shutting down")
    # set the event to signal threads
    raise StopMonitoring


class StopMonitoring(Exception):
    """
    This is a custom exception that gets thrown by the exit handler
    when SIGINT is detected. It allows a loop within a try/except block
    to break out and set the event to shutdown cleanly
    """

    pass


def upload_server_sync(sync_interval, rclone_config, upload_dir_pi, die, sync_trigger):
    logging.info("Function upload_server_sync has been called.")

    remote_name = rclone_config.get("remote_name", "mybox")
    config_path = rclone_config.get("config_path", "").strip()
    remote_base_path = rclone_config.get("remote_base_path", "monitoring_data")

    while not die.is_set():
        # Wait for trigger (instant) or timeout (sync_interval)
        sync_trigger.wait(timeout=sync_interval)
        sync_trigger.clear()

        if die.is_set():
            break

        # Check internet & synchronise
        if is_internet_available():
            logging.info("Internet detected. Starting immediate upload sync.")
            subprocess.call("bash ./update_time.sh", shell=True)

            # Prepare state file & log
            state_file = os.path.join(
                os.path.dirname(upload_dir_pi), "rclone_state.json"
            )
            logfile = os.path.join(os.path.dirname(upload_dir_pi), "rclone.log")

            exit_code = subprocess.call(
                [
                    "bash",
                    "./rclone_upload.sh",
                    upload_dir_pi,
                    remote_name,
                    state_file,
                    logfile,
                    config_path,
                    remote_base_path,
                ]
            )

            if exit_code != 0:
                logging.error("Upload sync failed with exit code {}".format(exit_code))
        else:
            logging.info("Internet not available. Skipping sync.")

        gc_and_log_memory("upload_server_sync")


def clean_dirs(working_dir, upload_dir, pre_upload_dir, clean_working_dir=True):
    """
    Function to tidy up the directory structure, optionally cleaning the working
    directory and removing empty directories in upload/pre-upload paths.

    Args
        working_dir: Path to the working directory
        upload_dir: Path to the upload directory
        clean_working_dir: Boolean, should working_dir be deleted at startup
    """

    if clean_working_dir:
        logging.info("Cleaning up working directory")
        shutil.rmtree(working_dir, ignore_errors=True)
    else:
        logging.info("Skipping working directory cleanup (wipe_data_on_boot disabled)")

    # Remove empty directories in the upload directory, from bottom up
    for subdir, dirs, files in os.walk(upload_dir, topdown=False):
        if not os.listdir(subdir):
            logging.info("Removing empty upload directory: {}".format(subdir))
            shutil.rmtree(subdir, ignore_errors=True)

        # Remove empty directories in the upload directory, from bottom up
    for subdir, dirs, files in os.walk(pre_upload_dir, topdown=False):
        if not os.listdir(subdir):
            logging.info("Removing empty pre upload directory: {}".format(subdir))
            shutil.rmtree(subdir, ignore_errors=True)


def purge_oldest_recording(upload_dir, threshold_percent=95):
    """
    Legacy helper intentionally kept as a no-op to avoid any automatic
    deletion of recorded data.
    """
    logging.info(
        "purge_oldest_recording() called but automatic deletion is disabled. "
        "No data was removed from {}.".format(upload_dir)
    )


def storage_check_shutdown(
    min_storage_required_gb=1.0, check_path="/", warn_storage_gb=None
):
    """
    Checks remaining storage before recording and performs safe shutdown when
    free space drops below the configured safety threshold.

    This function never deletes data.
    """

    if warn_storage_gb is None:
        warn_storage_gb = 4.0

    bytes_avail = psutil.disk_usage(check_path).free
    gb_avail = bytes_avail / 1024 / 1024 / 1024

    if gb_avail < warn_storage_gb:
        logging.warning(
            "Storage low on {}: {:.2f} GB free (warning threshold: {:.2f} GB).".format(
                check_path, gb_avail, warn_storage_gb
            )
        )

    if gb_avail < min_storage_required_gb:
        logging.info(
            "\nStorage below safe threshold on {}: {:.2f} GB free < {:.2f} GB. Safely shutting down.\n".format(
                check_path, gb_avail, min_storage_required_gb
            )
        )
        safe_shutdown()


def continuous_recording(
    sensor,
    working_dir,
    upload_dir,
    sensor_config,
    die,
    sync_trigger,
    test_mode,
    recording_in_progress=None,
    min_free_storage_gb=1.0,
    warn_free_storage_gb=4.0,
):
    """
    Runs a loop over the sensor sampling process
    Args:
        sensor: A instance of one of the sensor classes
        working_dir: Path to the working directory for recording
        upload_dir: Path to the final directory used to upload processed files
        sensor_config: The sensor configuration dictionary
        die: A threading event to terminate the upload server sync
        test_mode: Boolean, if True forces recording even if internet is available
    """

    # Require multiple consecutive tiny files before rebooting to avoid
    # reboot loops caused by one-off capture glitches on low-spec hardware.
    tiny_file_streak = 0
    tiny_file_reboot_threshold = 3

    # Start recording
    internet_paused_logged = False
    while not die.is_set():
        try:
            # Mandatorily process any pending recordings before starting a new one
            run_postprocess(sensor, upload_dir)

            # Check for internet to decide whether to record
            # Fix: Access offline_mode from root config (passed as sensor_config)
            force_record = sensor_config.get("offline_mode", 0) == 1

            # Check if sync is currently triggered
            is_syncing = sync_trigger.is_set()

            if (
                not force_record
                and (is_internet_available() or is_syncing)
                and not test_mode
            ):
                if not internet_paused_logged:
                    logging.info(
                        f"Upload in progress (internet={is_internet_available()}, syncing={is_syncing}); pausing record."
                    )
                    sync_trigger.set()  # Trigger sync immediately
                    internet_paused_logged = True
                time.sleep(
                    1
                )  # Small sleep to prevent CPU hogging while waiting for upload
                continue

            internet_paused_logged = False  # Reset flag when recording resumes

            # Never delete recorded data automatically. Only perform safety checks.
            storage_check_shutdown(
                min_storage_required_gb=min_free_storage_gb,
                check_path=upload_dir,
                warn_storage_gb=warn_free_storage_gb,
            )
            # Begin new recording. Sleep is handled separately below so that
            # recording_in_progress can be cleared before the capture_delay
            # window, giving the scheduled reboot monitor a chance to fire
            # between recordings rather than being blocked indefinitely.
            if recording_in_progress is not None:
                recording_in_progress.set()
            record_sensor(sensor, working_dir, upload_dir, sensor_config, sleep=False)
            if recording_in_progress is not None:
                recording_in_progress.clear()

            # Check if last recording file is too small and only reboot when
            # this happens repeatedly.
            if check_last_recording_size(upload_dir, "/home/pi/pre_upload_dir"):
                tiny_file_streak += 1
                logging.warning(
                    "Tiny file: {}/{} consecutive.".format(
                        tiny_file_streak, tiny_file_reboot_threshold
                    )
                )
                if tiny_file_streak >= tiny_file_reboot_threshold:
                    logging.warning(
                        "Repeated tiny recordings detected ({} consecutive). Rebooting system.".format(
                            tiny_file_streak
                        )
                    )
                    subprocess.call("sudo reboot", shell=True)
            else:
                tiny_file_streak = 0

            # Sleep between recordings with recording_in_progress cleared so
            # scheduled_reboot_monitor can trigger during the capture_delay.
            gc_and_log_memory("continuous_recording")
            sensor.sleep()

        except Exception as e:
            if recording_in_progress is not None:
                recording_in_progress.clear()
            logging.error(
                "continuous_recording: unhandled exception at {}: {}".format(
                    time.strftime("%Y-%m-%d %H:%M:%S"), e
                )
            )
            logging.error(traceback.format_exc())
            # Log disk usage snapshot for diagnosis.
            try:
                du = psutil.disk_usage(upload_dir)
                logging.warning(
                    "Disk: {:.1f} GB free / {:.1f} GB total.".format(
                        du.free / (1024**3),
                        du.total / (1024**3),
                    )
                )
            except Exception:
                pass
            time.sleep(5)


def record(config_file, logfile_name, log_dir="logs"):
    """
    Function to setup, run and log continuous sampling from the sensor.

    Args:
        config_file: The JSON config file to use to set up.
        logfile_name: The filename that the logs from this run should be stored to
        log_dir: A directory to be used for logging. Existing log files
        found in will be moved to upload.
    """

    # Start logging immediately. The log_dir can't be included in config
    # because we're not loading config until after logging has started.

    # Create the logs directory and file if needed
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, logfile_name)
    if not os.path.exists(logfile):
        open(logfile, "w+")

    # Add handlers to logging so logs are sent to stdout and the file
    logging.getLogger().setLevel(logging.INFO)
    minute_formatter = MinuteBoundaryFormatter()

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(minute_formatter)
    logging.getLogger().addHandler(ch)

    hdlr = logging.FileHandler(filename=logfile)
    hdlr.setFormatter(minute_formatter)
    logging.getLogger().addHandler(hdlr)

    # Load the cpu_serial from environment variable
    try:
        cpu_serial = os.environ["PI_ID"]
    except KeyError:
        logging.error("No environment variable set for cpu_serial")
        cpu_serial = "CPU_SERIAL_ERROR"

    start_time = datetime.now().strftime("%Y%m%d_%H%M")

    logging.info("Start of continuous sampling: {}".format(start_time))

    # Perform auto-update
    auto_update_repository()

    # Reload systemd daemon to pick up any potential service file changes
    try:
        logging.info("Reloading systemd daemon...")
        subprocess.call(["sudo", "systemctl", "daemon-reload"], timeout=10)
    except Exception as e:
        logging.warning("Failed to reload systemd daemon: {}".format(e))

    # Log current git commit information
    p = subprocess.Popen(["git", "log", "-1", '--format="%H"'], stdout=subprocess.PIPE)
    (stdout, _) = p.communicate()
    logging.info("Current git commit hash: {}".format(stdout.strip()))

    # Load the config file
    try:
        config = json.load(open(config_file))
        logging.info("Config file found")
    except IOError:
        logging.critical("Config file not found")
        sys.exit()

    try:
        sys_config = config["sys"]
        rclone_config = config["rclone"]
        sensor_config = config["sensor"]
        offline_mode = config["offline_mode"]
        test_mode = config.get("test_mode", 0) == 1
        force_offline_mode = str(
            os.environ.get("FORCE_OFFLINE_MODE", "0")
        ).strip().lower() in ["1", "true", "yes", "on"]
        working_dir = sys_config["working_dir"]
        upload_dir = sys_config["upload_dir"]
        min_free_storage_gb = float(sys_config.get("min_free_storage_gb", 1.0))
        warn_free_storage_gb = float(sys_config.get("warn_free_storage_gb", 4.0))
        if warn_free_storage_gb < min_free_storage_gb:
            warn_free_storage_gb = min_free_storage_gb
        reboot_times = parse_reboot_times(sys_config)
        use_system_shutdown_button = str(
            sys_config.get("use_system_shutdown_button", 0)
        ).strip().lower() in ["1", "true", "yes", "on"]
        if force_offline_mode:
            offline_mode = 1
            logging.info(
                "FORCE_OFFLINE_MODE detected: upload synchronisation disabled for this run"
            )
        logging.info("Config loaded")
    except KeyError:
        logging.info("Failed to load config")
        sys.exit()

    # Setup GPIO for sensors that have a button
    logging.info(
        f"DEBUG: Setup starting. offline_mode={offline_mode}, test_mode={test_mode}"
    )
    GPIO.setmode(GPIO.BCM)

    # Setup button for Respeaker series (GPIO 26)
    if sensor_config["sensor_type"] in [
        "Respeaker6Mic",
        "Respeaker4Mic",
        "Respeaker_Custom",
    ]:
        if use_system_shutdown_button:
            logging.info(
                "System-level shutdown button enabled; skipping Python GPIO button listener for Respeaker."
            )
        else:
            GPIO.setup(array_mic_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            try:
                GPIO.add_event_detect(
                    array_mic_button,
                    GPIO.FALLING,
                    callback=interrupt_button_callback,
                    bouncetime=100,
                )
            except RuntimeError as e:
                logging.warning(
                    "Failed to add GPIO edge detection on pin {} ({}). "
                    "Continuing without Python button listener. "
                    "If using dtoverlay gpio-shutdown, set sys.use_system_shutdown_button=1.".format(
                        array_mic_button, e
                    )
                )

    # Note: Sipeed7Mic uses system-level GPIO shutdown via dtoverlay in /boot/config.txt
    # No Python GPIO setup needed for Sipeed7Mic button

    if reboot_times:
        logging.info(
            "Configured daily reboot times: {}".format(", ".join(reboot_times))
        )
    else:
        logging.warning(
            "No valid daily reboot times configured; scheduled reboot disabled"
        )

    logging.info(
        "Storage safety policy: no auto-delete, warn below {:.2f} GB, shutdown below {:.2f} GB".format(
            warn_free_storage_gb, min_free_storage_gb
        )
    )

    # Schedule a shutdown after X hours, based on battery life...
    # Set the number a couple hours lower than expected (to be safe)
    # estimated_battery_hours = 40
    # minutes = estimated_battery_hours*60
    # logging.info('Scheduling battery life shutdown in {} minutes'.format(minutes))
    # battery_shutdown_cmd = 'sudo shutdown -h +{}'.format(minutes)
    # subprocess.call(battery_shutdown_cmd, shell=True)

    # Check working directory
    logging.info("DEBUG: Working directory check.")
    if os.path.exists(working_dir) and os.path.isdir(working_dir):
        logging.info("Using {} as working directory".format(working_dir))
    else:
        try:
            os.makedirs(working_dir)
            logging.info("Created {} as working directory".format(working_dir))
        except OSError:
            logging.critical(
                "Could not create {} as working directory".format(working_dir)
            )
            sys.exit()

    # Check for / create a directory for pre-compression files
    # output from this raspberry pi.
    pre_upload_dir = "/home/pi/pre_upload_dir"
    if not os.path.exists(pre_upload_dir):
        try:
            os.makedirs(pre_upload_dir)
            logging.info("Created {} as pre-upload directory".format(pre_upload_dir))
        except OSError:
            logging.critical(
                "Could not create {} as pre-upload directory".format(pre_upload_dir)
            )
            sys.exit()
    else:
        logging.info("Using {} as pre-upload directory".format(pre_upload_dir))

    # Check for / create an upload directory with a specific folder for
    # output from this raspberry pi.
    upload_dir = os.path.join(upload_dir)
    upload_dir_pi = os.path.join(upload_dir, "live_data", cpu_serial)
    if os.path.exists(upload_dir_pi) and os.path.isdir(upload_dir_pi):
        logging.info("Using {} as upload directory".format(upload_dir_pi))
    else:
        try:
            os.makedirs(upload_dir_pi)
            logging.info("Created {} as upload directory".format(upload_dir_pi))
        except OSError:
            logging.critical(
                "Could not create {} as upload directory".format(upload_dir_pi)
            )
            sys.exit()

    # Never wipe upload/live data at boot from recorder runtime.
    clean_dirs(working_dir, upload_dir, pre_upload_dir, clean_working_dir=False)

    # move any existing logs into the upload folder for this pi
    try:
        upload_dir_logs = os.path.join(upload_dir_pi, "logs")
        if not os.path.exists(upload_dir_logs):
            os.makedirs(upload_dir_logs)

        existing_logs = [
            f for f in os.listdir(log_dir) if f.endswith(".log") and f != logfile_name
        ]
        for log in existing_logs:
            os.rename(os.path.join(log_dir, log), os.path.join(upload_dir_logs, log))
            logging.info("Moved {} to upload".format(log))
    except OSError:
        # not critical - can leave logs in the log_dir
        logging.error("Could not move existing logs to upload.")

    # Now get the sensor
    logging.info("DEBUG: Configuring sensor.")
    sensor = configure_sensor(sensor_config)

    # Set up the threads to run and an event handler to allow them to be shutdown cleanly
    logging.info("DEBUG: Setting up threads.")
    die = threading.Event()
    sync_trigger = threading.Event()
    signal.signal(signal.SIGINT, exit_handler)

    if not offline_mode and not test_mode:
        sync_thread = threading.Thread(
            target=upload_server_sync,
            args=(
                sensor.server_sync_interval,
                rclone_config,
                upload_dir_pi,
                die,
                sync_trigger,
            ),
        )

    reboot_thread = None
    recording_in_progress = threading.Event()
    if reboot_times:
        reboot_thread = threading.Thread(
            target=scheduled_reboot_monitor,
            args=(reboot_times, die, recording_in_progress),
        )

    record_thread = threading.Thread(
        target=continuous_recording,
        args=(
            sensor,
            working_dir,
            upload_dir_pi,
            config,
            die,
            sync_trigger,
            test_mode,
            recording_in_progress,
            min_free_storage_gb,
            warn_free_storage_gb,
        ),
    )

    # Initialise background thread to do remote sync of the root upload directory
    # Failure here does not preclude data capture and might be temporary so log
    # errors but don't exit.
    try:
        logging.info(
            "Starting continuous recording at {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        # Drain any pending files from previous sessions before the recording
        # thread is allowed to start. This is a blocking call — the thread
        # cannot begin until every queued WAV has been converted to FLAC (or
        # discarded if too small / corrupted).
        logging.info("Draining pending queue before first recording...")
        run_postprocess(sensor, upload_dir_pi)
        logging.info("Queue drained. Starting recording.")

        record_thread.start()
        if reboot_thread is not None:
            reboot_thread.start()

        if offline_mode:
            logging.info("Running in offline mode - no upload synchronisation")
        elif test_mode:
            logging.info("Running in test mode - upload synchronisation disabled")
        else:
            logging.info("DEBUG: Entering else block for sync_thread.")
            # Start sync thread immediately
            sync_thread.start()
            logging.info("Thread upload sync has started.")
            logging.info(
                "Starting upload server sync every {} seconds at {}".format(
                    sensor.server_sync_interval,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                )
            )

        # now run a loop that will continue with a small grain until
        # an interrupt arrives, this is necessary to keep the program live
        # and listening for interrupts
        while True:
            time.sleep(1)
    except StopMonitoring:
        # We've had an interrupt signal, so tell the threads to shutdown,
        # wait for them to finish and then exit the program
        die.set()
        record_thread.join()
        if reboot_thread is not None:
            reboot_thread.join()
        if not offline_mode:
            sync_thread.join()

        logging.info(
            "Recording and sync shutdown, exiting at {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )


# On button press, safely shutdown the pi...
def interrupt_button_callback(channel):
    logging.info("\nButton press detected. Safely shutting down.\n")
    safe_shutdown()


if __name__ == "__main__":
    # run record with three arguements - the path to the config file, the log directory and the log
    record(sys.argv[1], sys.argv[2], sys.argv[3])
