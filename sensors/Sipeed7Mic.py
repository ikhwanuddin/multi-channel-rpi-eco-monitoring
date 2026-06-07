import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time

import sensors
from sensors.SensorBase import SensorBase


class Sipeed7Mic(SensorBase):
    # WAV files smaller than 1 MB are considered invalid for this pipeline.
    MIN_VALID_AUDIO_BYTES = 1024 * 1024

    def __init__(self, config=None):
        """
        A class to record audio from a USB Soundcard microphone.

        Args:
            config: A dictionary loaded from a config JSON file used to update
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

        # Auto-detect USB audio card
        self.card = self.find_usb_audio_card()

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

    @staticmethod
    def find_usb_audio_card():
        """
        Method to automatically detect the USB audio card number for recording.
        Targets USB audio devices like MicArray or USB-Audio. Returns the card
        number as a string, defaulting to '1' if not found.
        """
        raw_output = ""
        try:
            result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True, timeout=10
            )
            raw_output = result.stdout or ""
            logging.debug(
                "find_usb_audio_card: arecord -l stdout:\n{}".format(raw_output)
            )
            lines = raw_output.split("\n")
            for line in lines:
                if "MicArray" in line or "USB" in line:
                    # Parse card number, e.g., "card 2: MicArray [SipeedUSB MicArray]"
                    parts = line.split()
                    if len(parts) > 1 and parts[0] == "card":
                        card_num = parts[1].rstrip(":")
                        logging.info("Detected USB audio card: {}".format(card_num))
                        return card_num
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            logging.warning(
                "find_usb_audio_card: command failed: {}. "
                "arecord may not be installed.".format(e)
            )
        logging.warning(
            "find_usb_audio_card: no Sipeed/USB card found in arecord -l output, "
            "falling back to default card '1'. Raw arecord -l output: {}".format(
                raw_output[:500] if raw_output else "(empty or failed)"
            )
        )
        return "1"  # Default fallback

    def setup(self):
        try:
            # Load alsactl file - increased microphone volume level
            ret = subprocess.call(
                "alsactl --file ./audio_sensor_scripts/asound.state restore",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
        record_result = None
        arecord_stderr = ""
        timeout_happened = False
        stderr_file = None
        file_size = 0
        try:
            card_arg = "plughw:{},0".format(self.card)
            cmd = [
                "sudo",
                "arecord",
                "-D",
                card_arg,
                "-f",
                "S16_LE",
                "-r",
                "16000",
                "-c",
                "8",
                "--duration",
                str(self.record_length),
                wfile,
            ]
            logging.info(
                "{} - arecord command: {}".format(self.current_file, " ".join(cmd))
            )

            # Allow additional grace on low-power Pi Zero 2W before declaring timeout.
            kill_time = max(int(self.record_length * 1.75), self.record_length + 180)
            logging.debug(
                "{} - arecord timeout set to {}s (record_length={}s)".format(
                    self.current_file, kill_time, self.record_length
                )
            )
            try:
                stderr_file = tempfile.TemporaryFile()
                record_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=stderr_file
                )
                record_process.wait(timeout=kill_time)
                record_result = subprocess.CompletedProcess(
                    cmd, record_process.returncode
                )
                stderr_file.seek(0)
                arecord_stderr = (
                    stderr_file.read().decode("utf-8", errors="replace").strip()
                )
                stderr_file.close()
                stderr_file = None
            except subprocess.TimeoutExpired:
                timeout_happened = True
                # Snapshot stderr before stopping the process.
                if stderr_file is not None:
                    stderr_file.seek(0)
                    arecord_stderr = (
                        stderr_file.read().decode("utf-8", errors="replace").strip()
                    )
                logging.warning(
                    "\n{} - arecord timed out after {}s; attempting graceful stop\n".format(
                        self.current_file, kill_time
                    )
                )
                # Graceful stop first so WAV headers/data can be finalized.
                record_process.terminate()
                try:
                    record_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logging.error(
                        "{} - arecord did not terminate gracefully, forcing kill".format(
                            self.current_file
                        )
                    )
                    record_process.kill()
                    record_process.wait(timeout=2)
                if stderr_file is not None:
                    # Re-read stderr now that process exited (additional lines).
                    stderr_file.seek(0)
                    arecord_stderr = (
                        stderr_file.read().decode("utf-8", errors="replace").strip()
                    )
                    stderr_file.close()
                    stderr_file = None
                record_result = subprocess.CompletedProcess(
                    cmd, record_process.returncode or 124
                )

            # --- Post-recording diagnostics ---
            file_exists = os.path.exists(wfile)
            file_size = os.path.getsize(wfile) if file_exists else 0

            # Log exit code and stderr on every recording attempt (success or failure).
            exit_code = record_result.returncode if record_result else -1
            timeout_tag = " timeout=true" if timeout_happened else ""
            logging.info(
                "{} - arecord exited with code={} file_size={} bytes{}".format(
                    self.current_file, exit_code, file_size, timeout_tag
                )
            )

            if arecord_stderr:
                # Full stderr — useful for catching overrun/underrun warnings
                # even when arecord exits 0.
                for line in arecord_stderr.splitlines():
                    logging.warning(
                        "{} - arecord-stderr: {}".format(self.current_file, line)
                    )

            # Remove file if too small and mark as missing.
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

            # Raise detailed RuntimeError when recording is considered failed.
            if record_result is not None and record_result.returncode != 0:
                raise RuntimeError(
                    "arecord exited with code {} | file_size={} bytes{} | "
                    "stderr: {}".format(
                        record_result.returncode,
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

            # Success path.
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
                f.write("sensor=Sipeed7Mic\n")
                f.write("card={}\n".format(self.card))
                f.write("error={}\n".format(str(exc)))
                f.write(
                    "exit_code={}\n".format(
                        record_result.returncode if record_result else "N/A"
                    )
                )
                f.write("file_size_bytes={}\n".format(file_size))
                f.write("timeout={}\n".format(timeout_happened))
                f.write("arecord_stderr={}\n".format(arecord_stderr))
            time.sleep(1)

        finally:
            if stderr_file is not None:
                try:
                    stderr_file.close()
                except Exception:
                    pass

        if record_succeeded:
            logging.info(
                "\n{} recording and transfer complete at {}\n".format(
                    self.current_file, time.strftime("%H-%M-%S")
                )
            )

    def postprocess(self, wfile, upload_dir):
        """
        On RPi Zero 2W the CPU is too slow for real-time FLAC compression.
        WAV files are already staged in pre_upload_dir by capture_data(); compression
        will be handled later by the upload pipeline's pre_upload_dir mechanism.
        """
        logging.info(
            "\n{} - Skipping compression on Sipeed (RPi Zero 2W); "
            "will be handled during upload".format(wfile)
        )


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
