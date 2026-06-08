import logging
import os
import subprocess
import sys
import time

import sensors
from sensors.SensorBase import SensorBase


class Respeaker6Mic(SensorBase):
    # WAV files smaller than 1 MB are considered invalid for this pipeline.
    MIN_VALID_AUDIO_BYTES = 1024 * 1024

    def __init__(self, config=None):
        """
        A class to record audio from a USB Soundcard microphone.

        Args:
            config: A dictionary loaded from a config JSON file used to replace
            the default settings of the sensor.
        """

        # Initialise the sensor config, double checking the types of values. This
        # code uses the variables named and described in the config static to set
        # defaults and override with any passed in the config file.
        opts = self.options()
        opts = {var["name"]: var for var in opts}

        self.record_length = sensors.set_option("record_length", config, opts)
        self.compress_data = sensors.set_option("compress_data", config, opts)
        self.capture_delay = sensors.set_option("capture_delay", config, opts)

        # set internal variables and required class variables
        self.working_file = "currentlyRecording.wav"
        self.current_file = None
        self.working_dir = None
        self.upload_dir = None
        self.pre_upload_dir = "/home/pi/pre_upload_dir"
        self.server_sync_interval = self.record_length + self.capture_delay

    @staticmethod
    def options():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [
            {
                "name": "record_length",
                "type": int,
                "default": 1200,
                "prompt": "What is the time in seconds of the audio segments?",
            },
            {
                "name": "compress_data",
                "type": bool,
                "default": True,
                "prompt": "Should the audio data be compressed from WAV to FLAC Lossless Compression?",
            },
            {
                "name": "capture_delay",
                "type": int,
                "default": 300,
                "prompt": "How long should the system wait between audio samples?",
            },
        ]

    def setup(self):
        try:
            # Load alsactl file - increased microphone volume level
            ret = subprocess.call(
                "alsactl --file ./audio_sensor_scripts/asound.state restore",
                shell=True,
            )
            if ret != 0:
                logging.warning(
                    "alsactl restore exited with code {}; audio mixer levels "
                    "may not be applied.".format(ret)
                )
            return True
        except Exception:
            raise EnvironmentError

    def capture_data(self, working_dir, upload_dir, pre_upload_dir):
        """
        Method to capture raw audio data from the USB Soundcard Mic

        Args:
            working_dir: A working directory to use for file processing
            upload_dir: The directory to write the final data file to for upload.
        """

        # populate the working and upload directories
        self.working_dir = working_dir
        self.upload_dir = upload_dir
        self.pre_upload_dir = pre_upload_dir

        # Name files by start time and duration
        start_time = time.strftime("%H-%M-%S")
        self.current_file = "{}_dur={}secs".format(start_time, self.record_length)

        # Record for a specific duration
        wfile = os.path.join(self.working_dir, self.current_file)
        ofile = os.path.join(self.pre_upload_dir, self.current_file)
        logging.info(
            "\n{} - Started recording at {}".format(self.current_file, start_time)
        )
        record_succeeded = False
        arecord_exit_code = -1
        arecord_stderr = ""
        timeout_happened = False
        file_size = 0

        try:
            cmd_str = "arecord -Dac108 -f S32_LE -r 16000 -c 6 --duration {} {}"
            full_cmd = cmd_str.format(self.record_length, wfile)
            logging.info("{} - arecord command: {}".format(self.current_file, full_cmd))

            # To remedy unexpected recording faults
            kill_time = self.record_length * 1.1
            logging.debug(
                "{} - arecord timeout set to {:.1f}s (record_length={}s)".format(
                    self.current_file, kill_time, self.record_length
                )
            )

            # Use Popen to capture stderr (cannot easily capture stderr with
            # subprocess.call + shell=True, so use Popen with a shell wrapper).
            try:
                arecord_process = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                try:
                    stdout_data, stderr_data = arecord_process.communicate(
                        timeout=kill_time
                    )
                    arecord_exit_code = arecord_process.returncode
                    arecord_stderr = (
                        stderr_data.decode("utf-8", errors="replace").strip()
                        if stderr_data
                        else ""
                    )
                except subprocess.TimeoutExpired:
                    timeout_happened = True
                    # Snapshot stderr before killing.
                    try:
                        arecord_process.kill()
                        stdout_data, stderr_data = arecord_process.communicate(
                            timeout=5
                        )
                        arecord_exit_code = arecord_process.returncode or 124
                        arecord_stderr = (
                            stderr_data.decode("utf-8", errors="replace").strip()
                            if stderr_data
                            else ""
                        )
                    except subprocess.TimeoutExpired:
                        arecord_exit_code = -9
                        arecord_stderr = "(force-kill timed out)"
                    logging.warning(
                        "\n{} - arecord timed out after {:.1f}s\n".format(
                            self.current_file, kill_time
                        )
                    )
                    # Also kill any lingering arecord processes.
                    subprocess.run(
                        "pkill -9 arecord", shell=True, stderr=subprocess.DEVNULL
                    )
            except Exception as proc_exc:
                arecord_exit_code = -1
                arecord_stderr = str(proc_exc)
                logging.error(
                    "{} - failed to launch arecord: {}".format(
                        self.current_file, proc_exc
                    )
                )

            # --- Post-recording diagnostics ---
            file_exists = os.path.exists(wfile)
            file_size = os.path.getsize(wfile) if file_exists else 0

            timeout_tag = " timeout=true" if timeout_happened else ""
            logging.info(
                "{} - arecord exited with code={} file_size={} bytes{}".format(
                    self.current_file, arecord_exit_code, file_size, timeout_tag
                )
            )

            if arecord_stderr:
                for line in arecord_stderr.splitlines():
                    logging.warning(
                        "{} - arecord-stderr: {}".format(self.current_file, line)
                    )

            # Remove file if too small.
            if file_exists and file_size < self.MIN_VALID_AUDIO_BYTES:
                logging.warning(
                    "{} - recorded file {:.2f} KB below minimum {:.2f} KB; "
                    "discarding".format(
                        self.current_file,
                        file_size / 1024.0,
                        self.MIN_VALID_AUDIO_BYTES / 1024.0,
                    )
                )
                os.remove(wfile)
                file_exists = False

            # Validate recording result.
            if arecord_exit_code != 0:
                raise RuntimeError(
                    "arecord exited with code {} | file_size={} bytes{} | "
                    "stderr: {}".format(
                        arecord_exit_code,
                        file_size,
                        timeout_tag,
                        _truncate_stderr(arecord_stderr),
                    )
                )

            if not file_exists:
                raise RuntimeError(
                    "Recorded file missing or too small ({} bytes){} | "
                    "stderr: {}".format(
                        file_size,
                        timeout_tag,
                        _truncate_stderr(arecord_stderr),
                    )
                )

            # Success path: rename to pre-upload dir.
            self.uncomp_file_name = ofile + ".wav"
            os.rename(wfile, self.uncomp_file_name)
            logging.info(
                "{} - recording success, {:.2f} KB transferred to {}".format(
                    self.current_file, file_size / 1024.0, self.uncomp_file_name
                )
            )
            record_succeeded = True

        except Exception as exc:
            if os.path.exists(wfile):
                try:
                    os.remove(wfile)
                except OSError:
                    pass
            logging.error(
                "{} - Error recording from audio card: {}".format(
                    self.current_file, exc
                )
            )
            marker_file = ofile + "_ERROR_audio-record-failed"
            with open(marker_file, "w") as f:
                f.write("time={}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                f.write("sensor=Respeaker6Mic\n")
                f.write("error={}\n".format(str(exc)))
                f.write("exit_code={}\n".format(arecord_exit_code))
                f.write("file_size_bytes={}\n".format(file_size))
                f.write("timeout={}\n".format(timeout_happened))
                f.write("arecord_stderr={}\n".format(arecord_stderr))
            time.sleep(1)

        if record_succeeded:
            logging.info(
                "\n{} recording and transfer complete at {}\n".format(
                    self.current_file, time.strftime("%H-%M-%S")
                )
            )

    def postprocess(self, wfile, upload_dir):
        """
        Method to optionally compress raw audio data to FLAC and stage data to
        upload folder
        """

        pre_upload_dir = "/home/pi/pre_upload_dir"

        # Get File Location Infor for correct upload
        file_path = wfile.split(os.sep)
        filename = file_path[5]
        start_date = file_path[4]

        # Make sure relevant upload dir exists
        session_upload_dir = os.path.join(upload_dir, start_date)

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

        # Determine Path for Postprocessed Files:
        ofile = wfile.replace(pre_upload_dir, upload_dir)

        if self.compress_data:
            # Get Filename Ready for Compression
            ofile = ofile.replace(".wav", ".flac")

            # Audio is compressed using a FLAC Encoding
            try:
                logging.info(
                    "\n Starting compression of {} to {} at {}\n".format(
                        wfile, ofile, time.strftime("%H-%M-%S")
                    )
                )
                # Use FLAC level 2 (fast) instead of default 5 (medium) for RPi performance
                ffmpeg_cmd = "ffmpeg -i {} -c:a flac -compression_level 2 {}".format(
                    wfile, ofile
                )
                logging.debug("ffmpeg command: {}".format(ffmpeg_cmd))
                ff_ret = subprocess.call(ffmpeg_cmd, shell=True)
                if ff_ret != 0:
                    logging.error(
                        "ffmpeg compression exited with code {} for {}".format(
                            ff_ret, wfile
                        )
                    )
                else:
                    os.remove(wfile)
                    logging.info(
                        "\n Finished compression of {} to {} at {}\n".format(
                            wfile, ofile, time.strftime("%H-%M-%S")
                        )
                    )
            except Exception as exc:
                logging.error("Error compressing {}: {}".format(wfile, exc))

        else:
            # Don't compress, store as wav
            logging.info("\n{} - No postprocessing of audio data\n".format(wfile))
            os.rename(wfile, ofile)


def _truncate_stderr(stderr, max_lines=10):
    """Helper: return stderr trimmed to last `max_lines` lines."""
    if not stderr:
        return "(no stderr)"
    lines = stderr.splitlines()
    if len(lines) <= max_lines:
        return stderr
    return "(... {} earlier lines omitted)\n{}".format(
        len(lines) - max_lines,
        "\n".join(lines[-max_lines:]),
    )
