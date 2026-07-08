# Sequencer Engine for ESP32-S3 Show Sequencer

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import sys

# --- Playback States ---
STATE_IDLE = 0
STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_STOPPED = 3

class ShowStopped(Exception):
    """Exception raised to terminate a running sequence immediately and cleanly."""
    pass

class Sequencer:
    def __init__(self, devices, blynk_client=None):
        self.devices = devices
        self.blynk = blynk_client
        self.state = STATE_IDLE
        self.current_sequence_name = None
        self._run_task = None
        self._status_callback = None

    def set_status_callback(self, cb):
        """Register a callback to notify Blynk or log changes in sequencer status."""
        self._status_callback = cb

    def update_status(self, status_msg):
        print("SEQUENCER STATUS: {}".format(status_msg))
        if self._status_callback:
            self._status_callback(status_msg)

    def load_sequence_module(self, name):
        """Dynamically load or reload a python sequence module from the filesystem."""
        try:
            # Force reload by deleting from sys.modules if it was previously imported
            if name in sys.modules:
                del sys.modules[name]
            
            # Import the module
            module = __import__(name)
            self.current_sequence_name = name
            return module
        except Exception as e:
            self.update_status("LOAD ERROR: {}".format(str(e)))
            print("Failed to load sequence '{}': {}".format(name, e))
            return None

    async def sleep(self, duration_sec):
        """Cooperative async sleep. Checks for PAUSED or STOPPED states at high frequency."""
        elapsed = 0.0
        check_interval = 0.05  # Check state every 50ms
        
        while elapsed < duration_sec:
            # Check for stop state
            if self.state == STATE_STOPPED:
                raise ShowStopped()
                
            # Handle pause state
            while self.state == STATE_PAUSED:
                await asyncio.sleep(check_interval)
                if self.state == STATE_STOPPED:
                    raise ShowStopped()
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval

    async def _run_wrapper(self, run_func):
        """Executes the sequence coroutine and handles state transitions and cleanups."""
        try:
            self.state = STATE_PLAYING
            self.update_status("PLAYING")
            await run_func(self.devices, self)
            self.state = STATE_IDLE
            self.update_status("IDLE")
        except ShowStopped:
            self.state = STATE_IDLE
            self.update_status("IDLE")
            print("Show stopped by user request.")
        except Exception as e:
            self.state = STATE_IDLE
            self.update_status("ERROR: {}".format(str(e)))
            print("Exception in show sequence execution:")
            sys.print_exception(e)
        finally:
            # Turn off all devices (emergency stop / safety cleanup)
            self.devices.stop_all()
            self._run_task = None

    def play(self, sequence_name):
        """Start playing a show sequence by name."""
        if self.state == STATE_PLAYING or self.state == STATE_PAUSED:
            print("Sequence already running. Stopping previous first.")
            self.stop()
            
        module = self.load_sequence_module(sequence_name)
        if not module:
            return False

        if not hasattr(module, "run_sequence"):
            self.update_status("RUN ERROR: no run_sequence()")
            print("Error: module '{}' does not define run_sequence(devices, sequencer)".format(sequence_name))
            return False

        self.state = STATE_PLAYING
        # Launch sequence task in the asyncio loop
        self._run_task = asyncio.create_task(self._run_wrapper(module.run_sequence))
        return True

    def stop(self):
        """Stop sequence execution immediately and shut down devices."""
        if self.state in (STATE_PLAYING, STATE_PAUSED):
            self.state = STATE_STOPPED
            # We don't cancel the task directly, instead we let the next sleep check raise ShowStopped.
            # This allows the sequence's 'try-finally' blocks to clean up resources.
            print("Stopping sequence...")
        else:
            print("Stop request ignored (Sequencer is IDLE)")

    def pause(self):
        """Pause show sequence execution (break)."""
        if self.state == STATE_PLAYING:
            self.state = STATE_PAUSED
            self.update_status("PAUSED")
            print("Sequence paused.")

    def resume(self):
        """Resume paused show sequence execution (continue)."""
        if self.state == STATE_PAUSED:
            self.state = STATE_PLAYING
            self.update_status("PLAYING")
            print("Sequence resumed.")
