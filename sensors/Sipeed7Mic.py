import time
import subprocess
import tempfile
import os
import sensors
import logging
import sys
from sensors.SensorBase import SensorBase

class Sipeed7Mic(SensorBase):

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
        opts = {var['name']: var for var in opts}

        self.record_length = sensors.set_option('record_length', config, opts)
        self.compress_data = sensors.set_option('compress_data', config, opts)
        self.capture_delay = sensors.set_option('capture_delay', config, opts)

        # Auto-detect USB audio card
        self.card = self.find_usb_audio_card()

        # set internal variables and required class variables
        self.working_file = 'currentlyRecording.wav'
        self.current_file = None
        self.working_dir = None
        self.upload_dir = None
        self.pre_upload_dir = '/home/pi/pre_upload_dir'
        self.server_sync_interval = self.record_length + self.capture_delay

    @staticmethod
    def options():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'record_length',
                 'type': int,
                 'default': 1200,
                 'prompt': 'What is the time in seconds of the audio segments?'},
                {'name': 'compress_data',
                 'type': bool,
                 'default': True,
                 'prompt': 'Should the audio data be compressed from WAV to FLAC Lossless Compression?'},
                {'name': 'capture_delay',
                 'type': int,
                 'default': 300,
                 'prompt': 'How long should the system wait between audio samples?'}
                ]

    @staticmethod
    def find_usb_audio_card():
        """
        Method to automatically detect the USB audio card number for recording.
        Targets USB audio devices like MicArray or USB-Audio. Returns the card number as a string, defaulting to '1' if not found.
        """
        try:
            result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'MicArray' in line or 'USB' in line:
                    # Parse card number, e.g., "card 2: MicArray [SipeedUSB MicArray]"
                    parts = line.split()
                    if len(parts) > 1 and parts[0] == 'card':
                        card_num = parts[1].rstrip(':')
                        logging.info("Detected USB audio card: {}".format(card_num))
                        return card_num
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning("Failed to detect USB audio card: {}, using default '1'".format(e))
        logging.warning("USB audio card not found, using default '1'")
        return '1'  # Default fallback

    def setup(self):

        try:
            # Load alsactl file - increased microphone volume level
            subprocess.call('alsactl --file ./audio_sensor_scripts/asound.state restore', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
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
        start_time = time.strftime('%H-%M-%S')
        self.current_file = '{}_dur={}secs'.format(start_time, self.record_length)

        # Record for a specific duration
        wfile = os.path.join(self.working_dir, self.current_file)
        ofile = os.path.join(self.pre_upload_dir, self.current_file)
        logging.info('\n{} - Started recording at {}'.format(self.current_file, start_time))
        record_result = None
        arecord_stderr = ''
        try:
            cmd = ['sudo', 'arecord', '-D', 'plughw:{},0'.format(self.card), '-f', 'S16_LE', '-r', '16000', '-c', '8', '--duration', str(self.record_length), wfile]
            
            # To remedy unexpected recording faults

            kill_time = self.record_length * 1.5
            try:
                stderr_file = tempfile.TemporaryFile()
                record_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=stderr_file)
                record_process.wait(timeout=kill_time)
                record_result = subprocess.CompletedProcess(cmd, record_process.returncode)
                stderr_file.seek(0)
                arecord_stderr = stderr_file.read().decode('utf-8', errors='replace').strip()
                stderr_file.close()
            except subprocess.TimeoutExpired:
                logging.info('\n{} - Timed Out \n'.format(self.current_file))
                # Graceful stop first so WAV headers/data can be finalized.
                record_process.terminate()
                try:
                    record_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logging.info('{} - arecord did not terminate gracefully, forcing kill'.format(self.current_file))
                    record_process.kill()
                    record_process.wait(timeout=2)
                stderr_file.seek(0)
                arecord_stderr = stderr_file.read().decode('utf-8', errors='replace').strip()
                stderr_file.close()
                record_result = subprocess.CompletedProcess(cmd, record_process.returncode or 124)

            end_time = time.strftime('%H-%M-%S')
            logging.info('\n{} - Finished recording at {}'.format(self.current_file, end_time))

            if record_result is not None and record_result.returncode != 0:
                stderr_preview = ' | '.join(arecord_stderr.splitlines()[-3:]) if arecord_stderr else 'no stderr'
                raise RuntimeError('arecord exited with status {} | stderr: {}'.format(record_result.returncode, stderr_preview))

            if (not os.path.exists(wfile)) or (os.path.getsize(wfile) < self.MIN_VALID_AUDIO_BYTES):
                if os.path.exists(wfile):
                    file_size = os.path.getsize(wfile)
                    os.remove(wfile)
                else:
                    file_size = 0
                stderr_preview = ' | '.join(arecord_stderr.splitlines()[-3:]) if arecord_stderr else 'no stderr'
                raise RuntimeError('Recorded file too small ({} bytes) | stderr: {}'.format(file_size, stderr_preview))

            self.uncomp_file_name = ofile + '.wav'
            os.rename(wfile, self.uncomp_file_name)
            logging.info('\n{} transferred to {}'.format(self.current_file, wfile))
        except Exception as exc:
            logging.info('Error recording from audio card: {}. Creating dummy file'.format(exc))
            open(ofile + '_ERROR_audio-record-failed', 'a').close()
            time.sleep(1)

        end_time = time.strftime('%H-%M-%S')
        logging.info('\n{} recording and transfer complete at {}\n'.format(self.current_file, end_time))
        

    def postprocess(self, wfile, upload_dir):
        """
        On RPi Zero 2W the CPU is too slow for real-time FLAC compression.
        WAV files are already staged in pre_upload_dir by capture_data(); compression
        will be handled later by the upload pipeline's pre_upload_dir mechanism.
        """
        logging.info('\n{} - Skipping compression on Sipeed (RPi Zero 2W); will be handled during upload'.format(wfile))
