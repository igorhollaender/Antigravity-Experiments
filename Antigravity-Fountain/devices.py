# Device Abstraction Layer for ESP32-S3 Show Sequencer

try:
    import machine
    import neopixel
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    print("[WARNING] 'machine' or 'neopixel' modules not found. Running in Mock Mode.")

# --- Mock Implementations for testing outside MicroPython ---
class MockPWM:
    def __init__(self, pin):
        self.pin = pin
        self._duty = 0
        self._freq = 1000
    def freq(self, f=None):
        if f is not None: self._freq = f
        return self._freq
    def duty(self, d=None):
        if d is not None: self._duty = d
        return self._duty
    def deinit(self):
        pass

class MockNeoPixel:
    def __init__(self, pin, num):
        self.pin = pin
        self.num = num
        self.pixels = [(0, 0, 0)] * num
    def __setitem__(self, index, val):
        self.pixels[index] = val
    def __getitem__(self, index):
        return self.pixels[index]
    def write(self):
        pass

class MockPin:
    OUT = 1
    IN = 0
    def __init__(self, pin_num, mode=1, value=0):
        self.pin_num = pin_num
        self.mode = mode
        self._val = value
    def value(self, v=None):
        if v is not None: self._val = v
        return self._val

# --- Hardware Device Classes ---

class MotorDevice:
    def __init__(self, pin_num, freq=1000):
        self.pin_num = pin_num
        self.freq = freq
        if MICROPYTHON:
            self.pwm = machine.PWM(machine.Pin(pin_num))
            self.pwm.freq(freq)
            self.pwm.duty(0)
        else:
            self.pwm = MockPWM(pin_num)
        self.speed = 0

    def set_speed(self, speed_percent):
        """Set motor speed from 0 to 100%"""
        self.speed = max(0, min(100, speed_percent))
        # MicroPython ESP32 PWM duty is 10-bit (0-1023)
        duty = int(self.speed / 100 * 1023)
        self.pwm.duty(duty)
        # Debug printing if Mock Mode
        if not MICROPYTHON:
            pass

    def stop(self):
        self.set_speed(0)


class NeoPixelDevice:
    def __init__(self, pin_num, num_pixels):
        self.pin_num = pin_num
        self.num_pixels = num_pixels
        if MICROPYTHON:
            self.np = neopixel.NeoPixel(machine.Pin(pin_num), num_pixels)
        else:
            self.np = MockNeoPixel(pin_num, num_pixels)

    def set_pixel(self, index, r, g, b):
        if 0 <= index < self.num_pixels:
            self.np[index] = (r, g, b)

    def set_all(self, r, g, b):
        for i in range(self.num_pixels):
            self.np[i] = (r, g, b)

    def show(self):
        self.np.write()

    def stop(self):
        self.set_all(0, 0, 0)
        self.show()


class AudioDevice:
    def __init__(self, tx_pin=None, rx_pin=None, baudrate=9600):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baudrate = baudrate
        self.volume = 100
        self.tempo = 100  # Default 100% tempo (or BPM)
        
        # In a real physical setup, we could initialize UART here:
        # if MICROPYTHON:
        #     self.uart = machine.UART(1, baudrate=baudrate, tx=tx_pin, rx=rx_pin)
        # else:
        #     self.uart = None
        
        print("AUDIO: Initialized on pins TX={}, RX={} @ {}".format(tx_pin, rx_pin, baudrate))

    def play(self, track_id, volume=None, tempo=None):
        """Play a specific track with optional volume and tempo overrides"""
        if volume is not None:
            self.volume = max(0, min(100, volume))
        if tempo is not None:
            self.tempo = max(50, min(200, tempo))
            
        print("AUDIO: Playing track {} [Vol: {}%, Tempo: {}%]".format(track_id, self.volume, self.tempo))
        # If we had a real hardware DFPlayer, we would construct serial command packets here:
        # cmd = bytearray([0x7E, 0xFF, 0x06, 0x03, 0x00, 0x00, track_id, 0xEF])
        # if self.uart: self.uart.write(cmd)

    def set_volume(self, volume):
        self.volume = max(0, min(100, volume))
        print("AUDIO: Set Volume to {}%".format(self.volume))

    def set_tempo(self, tempo):
        self.tempo = max(50, min(200, tempo))
        print("AUDIO: Set Tempo to {}%".format(self.tempo))

    def stop(self):
        print("AUDIO: Stopped playback")


class AuxDevice:
    def __init__(self, pin_num, device_type="digital"):
        self.pin_num = pin_num
        self.device_type = device_type
        if MICROPYTHON:
            self.pin = machine.Pin(pin_num, machine.Pin.OUT)
            self.pin.value(0)
        else:
            self.pin = MockPin(pin_num, MockPin.OUT)
        self.state = 0

    def control(self, command, *args, **kwargs):
        """Generic control command for the auxiliary device"""
        if command in ("ON", 1, True):
            self.state = 1
            self.pin.value(1)
            print("AUX (Pin {}): ON".format(self.pin_num))
        elif command in ("OFF", 0, False):
            self.state = 0
            self.pin.value(0)
            print("AUX (Pin {}): OFF".format(self.pin_num))
        else:
            print("AUX (Pin {}): Received command '{}' with args={}, kwargs={}".format(
                self.pin_num, command, args, kwargs
            ))

    def stop(self):
        self.control("OFF")


# --- Device Manager (Registry) ---

class DeviceManager:
    def __init__(self):
        self.motors = {}
        self.leds = None
        self.audio = None
        self.aux = {}

    def register_motor(self, index, pin_num):
        self.motors[index] = MotorDevice(pin_num)
        print("Register Motor {} on pin {}".format(index, pin_num))

    def register_leds(self, pin_num, num_pixels):
        self.leds = NeoPixelDevice(pin_num, num_pixels)
        print("Register NeoPixels on pin {} (count: {})".format(pin_num, num_pixels))

    def register_audio(self, tx_pin, rx_pin, baudrate=9600):
        self.audio = AudioDevice(tx_pin, rx_pin, baudrate)

    def register_aux(self, device_id, pin_num, device_type="digital"):
        self.aux[device_id] = AuxDevice(pin_num, device_type)
        print("Register Aux '{}' on pin {} (type: {})".format(device_id, pin_num, device_type))

    # --- Convenience Control Methods for Sequence Scripts ---
    
    def set_motor(self, index, speed_percent):
        if index in self.motors:
            self.motors[index].set_speed(speed_percent)
        else:
            print("[ERROR] Motor {} not registered".format(index))

    def set_led(self, index, r, g, b, flush=True):
        if self.leds:
            self.leds.set_pixel(index, r, g, b)
            if flush:
                self.leds.show()
        else:
            print("[ERROR] LEDs not registered")

    def set_all_leds(self, r, g, b):
        if self.leds:
            self.leds.set_all(r, g, b)
            self.leds.show()

    def play_audio(self, track_id, volume=None, tempo=None):
        if self.audio:
            self.audio.play(track_id, volume, tempo)
        else:
            print("[ERROR] Audio device not registered")

    def set_audio_volume(self, volume):
        if self.audio:
            self.audio.set_volume(volume)

    def set_audio_tempo(self, tempo):
        if self.audio:
            self.audio.set_tempo(tempo)

    def control_aux(self, device_id, command, *args, **kwargs):
        if device_id in self.aux:
            self.aux[device_id].control(command, *args, **kwargs)
        else:
            print("[ERROR] Aux device '{}' not registered".format(device_id))

    def stop_all(self):
        """Emergency stop / shutdown of all actuators"""
        print("Shutting down all actuators...")
        for motor in self.motors.values():
            motor.stop()
        if self.leds:
            self.leds.stop()
        if self.audio:
            self.audio.stop()
        for aux_dev in self.aux.values():
            aux_dev.stop()
