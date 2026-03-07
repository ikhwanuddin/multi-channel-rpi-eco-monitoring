#!/usr/bin/env python3
"""
clap_shutdown.py - Clap Detection for Safe Shutdown

This module continuously listens to the Sipeed 7-Mic Array via PyAudio,
detects a pattern of 3 claps within 2-3 seconds, and initiates a safe shutdown
after a 5-second confirmation period.

Features:
- RMS-based clap detection with configurable threshold
- Timing-based pattern recognition (3 claps, 0.3-1s intervals)
- 5-second confirmation window with LED blinking
- Background operation with low CPU usage
- Error handling for audio device issues
- Logging for debugging and monitoring

Usage:
    python3 clap_shutdown.py &
"""

import pyaudio
import numpy as np
import time
import subprocess
import logging
import sys
import os
from threading import Timer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'clap_shutdown.log'))
    ]
)

# Audio configuration
CHUNK = 1024  # Buffer size (about 0.05s at 16kHz)
FORMAT = pyaudio.paInt16
CHANNELS = 1  # Mono for simplicity (Sipeed 7-Mic is multichannel, but we use one channel)
RATE = 16000  # Sample rate (adjust if needed)

# Detection parameters
RMS_THRESHOLD = 0.1  # Adjust based on testing (0.0-1.0 normalized)
CLAP_WINDOW = 3.0  # Max time for 3 claps (seconds)
CLAP_INTERVAL_MIN = 0.3  # Min time between claps (seconds)
CLAP_INTERVAL_MAX = 1.0  # Max time between claps (seconds)
CONFIRMATION_TIME = 5.0  # Wait time before shutdown (seconds)

# LED scripts (if available)
LED_ON_SCRIPT = '/home/pi/multi-channel-rpi-eco-monitoring/led_on.sh'
LED_OFF_SCRIPT = '/home/pi/multi-channel-rpi-eco-monitoring/led_off.sh'

class ClapDetector:
    def __init__(self):
        self.audio = None
        self.stream = None
        self.clap_times = []
        self.confirmation_timer = None
        self.shutting_down = False

    def find_audio_device(self):
        """Find the Sipeed 7-Mic Array device index"""
        try:
            info = self.audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')

            for i in range(num_devices):
                device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
                name = device_info.get('name', '').lower()
                if 'micarray' in name or 'usb' in name or 'sipeed' in name:
                    logging.info(f"Found Sipeed device: {name} at index {i}")
                    return i

            # Fallback: try to find any USB audio device
            for i in range(num_devices):
                device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
                name = device_info.get('name', '').lower()
                if 'usb' in name:
                    logging.info(f"Found USB audio device: {name} at index {i}")
                    return i

            logging.warning("Sipeed 7-Mic Array not found, using default input device")
            return None
        except Exception as e:
            logging.error(f"Error finding audio device: {e}")
            return None

    def calculate_rms(self, data):
        """Calculate RMS of audio data"""
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            # Normalize to -1 to 1
            audio_data = audio_data.astype(np.float32) / 32768.0
            # Calculate RMS
            rms = np.sqrt(np.mean(audio_data**2))
            return rms
        except Exception as e:
            logging.error(f"Error calculating RMS: {e}")
            return 0.0

    def blink_led(self, duration=CONFIRMATION_TIME):
        """Blink LED during confirmation period"""
        if not os.path.exists(LED_ON_SCRIPT) or not os.path.exists(LED_OFF_SCRIPT):
            logging.warning("LED scripts not found, skipping LED blinking")
            return

        end_time = time.time() + duration
        while time.time() < end_time and not self.shutting_down:
            try:
                subprocess.run([LED_ON_SCRIPT], check=True, timeout=1)
                time.sleep(0.5)
                subprocess.run([LED_OFF_SCRIPT], check=True, timeout=1)
                time.sleep(0.5)
            except subprocess.TimeoutExpired:
                logging.warning("LED script timeout")
            except Exception as e:
                logging.error(f"Error blinking LED: {e}")
                break

    def check_recording_active(self):
        """Check if recording is currently active"""
        try:
            # Check if python_record.py process is running
            result = subprocess.run(['pgrep', '-f', 'python_record.py'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
            
            # Also check for currentlyRecording.wav file as backup
            if os.path.exists('/home/pi/multi-channel-rpi-eco-monitoring/currentlyRecording.wav'):
                return True
                
            return False
        except Exception as e:
            logging.warning(f"Error checking recording status: {e}")
            return False

    def initiate_shutdown(self):
        """Initiate safe shutdown"""
        logging.info("3 claps detected! Shutting down in 5 seconds...")
        self.shutting_down = True

        # Check if recording is active
        if self.check_recording_active():
            logging.warning("Recording is currently active! Initiating graceful shutdown of recording process first...")
            try:
                # Send SIGINT to python_record.py process for graceful shutdown
                subprocess.run(['pkill', '-INT', '-f', 'python_record.py'], timeout=5)
                logging.info("Sent SIGINT to recording process, waiting 10 seconds for cleanup...")
                time.sleep(10)  # Wait for recording to stop gracefully
            except Exception as e:
                logging.error(f"Error stopping recording process: {e}")

        # Start LED blinking in a separate thread
        import threading
        led_thread = threading.Thread(target=self.blink_led)
        led_thread.daemon = True
        led_thread.start()

        # Set timer for shutdown
        self.confirmation_timer = Timer(CONFIRMATION_TIME, self.perform_shutdown)
        self.confirmation_timer.start()

    def perform_shutdown(self):
        """Perform the actual shutdown"""
        logging.info("Executing safe system shutdown")
        try:
            subprocess.call(['sudo', 'shutdown', '-h', 'now'])
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")

    def detect_clap_pattern(self):
        """Check if clap times match the 3-clap pattern"""
        if len(self.clap_times) < 3:
            return False

        # Get last 3 claps
        recent_claps = self.clap_times[-3:]
        current_time = time.time()

        # Check if all claps are within the window
        if current_time - recent_claps[0] > CLAP_WINDOW:
            return False

        # Check intervals between claps
        for i in range(1, len(recent_claps)):
            interval = recent_claps[i] - recent_claps[i-1]
            if not (CLAP_INTERVAL_MIN <= interval <= CLAP_INTERVAL_MAX):
                return False

        return True

    def run(self):
        """Main detection loop"""
        try:
            self.audio = pyaudio.PyAudio()
            device_index = self.find_audio_device()

            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            logging.info("Clap detection started. Listening for 3 claps pattern...")

            last_clap_time = 0
            debounce_time = 0.2  # Minimum time between clap detections

            while not self.shutting_down:
                try:
                    data = self.stream.read(CHUNK, exception_on_overflow=False)
                    rms = self.calculate_rms(data)

                    current_time = time.time()

                    # Debug: uncomment to monitor RMS values
                    # if rms > 0.01:
                    #     logging.debug(f"RMS: {rms:.4f}")

                    # Detect clap
                    if rms > RMS_THRESHOLD and (current_time - last_clap_time) > debounce_time:
                        self.clap_times.append(current_time)
                        last_clap_time = current_time
                        logging.info(f"Clap detected! RMS: {rms:.4f}, Total claps: {len(self.clap_times)}")

                        # Keep only recent claps (within window + some buffer)
                        self.clap_times = [t for t in self.clap_times if current_time - t < CLAP_WINDOW + 1.0]

                        # Check for 3-clap pattern
                        if self.detect_clap_pattern():
                            self.initiate_shutdown()
                            break  # Exit loop after initiating shutdown

                        # If clap detected during confirmation, cancel shutdown
                        if self.confirmation_timer and self.confirmation_timer.is_alive():
                            self.cancel_shutdown()

                except IOError as e:
                    logging.error(f"Audio stream error: {e}")
                    time.sleep(1)  # Wait before retrying
                except Exception as e:
                    logging.error(f"Unexpected error in detection loop: {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Clap detection stopped by user")
        except Exception as e:
            logging.error(f"Error in clap detection: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
            logging.info("Clap detection terminated")

if __name__ == "__main__":
    detector = ClapDetector()
    detector.run()