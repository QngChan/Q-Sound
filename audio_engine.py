import sounddevice as sd
import numpy as np
import requests
from io import BytesIO
import threading
import pygame
import time

class AudioEngine:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except Exception as e:
            print(f"Pygame mixer init error: {e}")
            
        self.streams = []
        self.streams_lock = threading.Lock()
        
        # Mic Passthrough Stream
        self.passthrough_stream = None
        
        # Stop flag for playback
        self.stop_playback = threading.Event()
        self.volume = 1.0

    def get_input_devices(self):
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    input_devices.append({
                        "id": i,
                        "name": d['name']
                    })
            return input_devices
        except Exception as e:
            print(f"Error querying input devices: {e}")
            return []

    def get_output_devices(self):
        try:
            devices = sd.query_devices()
            output_devices = []
            for i, d in enumerate(devices):
                if d['max_output_channels'] > 0:
                    output_devices.append({
                        "id": i,
                        "name": d['name']
                    })
            return output_devices
        except Exception as e:
            print(f"Error querying output devices: {e}")
            return []

    def _play_worker(self, audio_data, sample_rate, device_id):
        stream = None
        try:
            channels = audio_data.shape[1] if len(audio_data.shape) > 1 else 1
            stream = sd.OutputStream(
                device=device_id,
                samplerate=sample_rate,
                channels=channels,
                dtype='float32'
            )
            
            with self.streams_lock:
                self.streams.append(stream)
            
            stream.start()
            
            # Chunked writing to allow for interruption
            chunk_size = 1024
            for i in range(0, len(audio_data), chunk_size):
                if self.stop_playback.is_set():
                    break
                # Apply volume and write chunk
                chunk = audio_data[i:i + chunk_size] * self.volume
                stream.write(chunk)
            
            stream.stop()
            
        except Exception as e:
            if not self.stop_playback.is_set():
                print(f"Stream error on device {device_id}: {e}")
        finally:
            if stream:
                try:
                    stream.close()
                except: pass
                with self.streams_lock:
                    if stream in self.streams:
                        self.streams.remove(stream)

    def stop_all(self):
        """
        Signals all playback workers to stop immediately.
        """
        print("Audio Engine: STOP SIGNAL SENT")
        self.stop_playback.set()
        
        # We don't hard-abort streams here to avoid driver crashes
        # The workers will check the flag and close themselves.
        
        # Optional: Short wait for threads to exit
        # threading.Thread(target=self._cleanup_flag).start()

    def _cleanup_flag(self):
        # Reset the stop flag after a bit so next play can start
        time.sleep(0.5)
        self.stop_playback.clear()

    def start_passthrough(self, input_id, output_id):
        """
        Routes microphone input directly to the selected output (e.g., Virtual Cable).
        """
        self.stop_passthrough()
        
        def callback(indata, outdata, frames, time, status):
            if status:
                print(f"Passthrough status: {status}")
            outdata[:] = indata
            
        try:
            print(f"Starting Mic Passthrough: IN={input_id}, OUT={output_id}")
            self.passthrough_stream = sd.Stream(
                device=(input_id, output_id),
                samplerate=None, # Auto
                channels=1,
                callback=callback
            )
            self.passthrough_stream.start()
            return True
        except Exception as e:
            print(f"Failed to start passthrough: {e}")
            return False

    def stop_passthrough(self):
        if self.passthrough_stream:
            try:
                self.passthrough_stream.stop()
                self.passthrough_stream.close()
            except: pass
            self.passthrough_stream = None
            print("Mic Passthrough Stopped.")

    def play_from_url(self, url, device_ids, on_finished_callback=None):
        try:
            self.stop_playback.clear() # Reset stop flag before starting
            response = requests.get(url, timeout=15)
            audio_bytes = BytesIO(response.content)
            
            try:
                sound = pygame.mixer.Sound(audio_bytes)
            except Exception as e:
                print(f"Decoder error: {e}")
                if on_finished_callback: on_finished_callback()
                return

            samples = pygame.sndarray.array(sound)
            if samples.dtype == np.int16:
                samples = samples.astype(np.float32) / 32768.0
            elif samples.dtype == np.int32:
                samples = samples.astype(np.float32) / 2147483648.0
            elif samples.dtype == np.uint8:
                samples = (samples.astype(np.float32) - 128.0) / 128.0
            
            if len(samples.shape) == 1:
                samples = samples.reshape(-1, 1)
            
            mixer_info = pygame.mixer.get_init()
            if not mixer_info:
                print("Mixer not initialized.")
                if on_finished_callback: on_finished_callback()
                return
            actual_rate, _, _ = mixer_info
            
            threads = []
            for dev_id in device_ids:
                t = threading.Thread(target=self._play_worker, args=(samples, actual_rate, dev_id), daemon=True)
                t.start()
                threads.append(t)
            
            if on_finished_callback:
                def watcher():
                    for t in threads:
                        t.join()
                    on_finished_callback()
                threading.Thread(target=watcher, daemon=True).start()
            
        except Exception as e:
            print(f"Playback logic error: {e}")
            if on_finished_callback: on_finished_callback()

if __name__ == "__main__":
    engine = AudioEngine()
    print("Audio Engine Ready.")
