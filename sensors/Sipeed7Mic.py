import time
import subprocess
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
                 'default': 120,
                 'prompt': 'What is the time in seconds of the audio segments?'},
                {'name': 'compress_data',
                 'type': bool,
                 'default': True,
                 'prompt': 'Should the audio data be compressed from WAV to FLAC Lossless Compression?'},
                {'name': 'capture_delay',
                 'type': int,
                 'default': 120,
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
        try:
            cmd = ['sudo', 'arecord', '-D', 'plughw:{},0'.format(self.card), '-f', 'S16_LE', '-r', '16000', '-c', '8', '--duration', str(self.record_length), wfile]
            
            # To remedy unexpected recording faults

            kill_time = self.record_length * 1.5
            try:
                record_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                record_process.wait(timeout=kill_time)
                record_result = subprocess.CompletedProcess(cmd, record_process.returncode)
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

                record_result = subprocess.CompletedProcess(cmd, record_process.returncode or 124)

            end_time = time.strftime('%H-%M-%S')
            logging.info('\n{} - Finished recording at {}'.format(self.current_file, end_time))

            if record_result is not None and record_result.returncode != 0:
                raise RuntimeError('arecord exited with status {}'.format(record_result.returncode))

            if (not os.path.exists(wfile)) or (os.path.getsize(wfile) < self.MIN_VALID_AUDIO_BYTES):
                if os.path.exists(wfile):
                    file_size = os.path.getsize(wfile)
                    os.remove(wfile)
                else:
                    file_size = 0
                raise RuntimeError('Recorded file too small ({} bytes), marking as invalid'.format(file_size))

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
        Method to optionally compress raw audio data to FLAC and stage data to
        upload folder
        """
        
        pre_upload_dir = '/home/pi/pre_upload_dir'

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
            logging.critical('Could not create upload directory for recording: \n{}'.format(session_upload_dir))
            sys.exit()

        # Determine Path for Postprocessed Files: 
        ofile= wfile.replace(pre_upload_dir, upload_dir)

        if (not os.path.exists(wfile)) or (os.path.getsize(wfile) < self.MIN_VALID_AUDIO_BYTES):
            logging.warning('Skipping compression for invalid or missing WAV: {}'.format(wfile))
            return

        if self.compress_data:

            # Get Filename Ready for Compression
            ofile = ofile.replace(".wav",".flac")
            
            time_now = time.strftime('%H-%M-%S')
            
            # Audio is compressed using a FLAC Encoding            
            try:
                logging.info('\nStarting compression of {}\nto {} at {}\n'.format(wfile, ofile, time_now))
                cmd = ['ffmpeg', '-y', '-i', wfile, '-c:a', 'flac', ofile]
                compress_result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if compress_result.returncode != 0:
                    raise RuntimeError('ffmpeg exited with status {}'.format(compress_result.returncode))
                if (not os.path.exists(ofile)) or (os.path.getsize(ofile) == 0):
                    raise RuntimeError('FLAC output missing or empty: {}'.format(ofile))
                os.remove(wfile)
                time_now = time.strftime('%H-%M-%S')
                logging.info('\nFinished compression of {}\nto {} at {}\n'.format(wfile, ofile, time_now))
            except Exception as exc:
                logging.info('Error compressing {}: {}'. format(wfile, exc))
            

        else:
            # Don't compress, store as wav
            logging.info('\n{} - No postprocessing of audio data'.format(wfile))
            os.rename(wfile, ofile)
