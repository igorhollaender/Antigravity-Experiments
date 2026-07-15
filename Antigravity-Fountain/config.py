# Configuration for ESP32-S3 Show Sequencer

# IH260713 Wifi ad Blynk credentials moved to config.toml
# # --- Wi-Fi Credentials ---
# # For Wokwi simulation, use "Wokwi-GUEST" with empty password
# WIFI_SSID = "Wokwi-GUEST"
# WIFI_PASS = ""

# # --- Blynk IoT Credentials ---
# # Replace these with your actual Blynk IoT credentials
# BLYNK_TEMPLATE_ID = "TMPLxxxxxx"
# BLYNK_TEMPLATE_NAME = "FountainSequencer"
# BLYNK_AUTH_TOKEN = "your_blynk_auth_token_here"

# --- Actuator / Device Pins ---
# Pump Motors (PWM-controlled)
MOTOR_PINS = [4, 5, 6]  # GPIO pins for Motors
MOTOR_FREQ = 1000       # 1kHz PWM frequency

# NeoPixel LEDs (WS2812B)
NEOPIXEL_PIN = 48       # GPIO pin for NeoPixel data
NEOPIXEL_NUM = 3        # Number of chained pixels

# Audio Settings
# We can configure UART parameters for a DFPlayer Mini if hardware is used
AUDIO_UART_PORT = 1      # UART1 for audio player
AUDIO_TX_PIN = 17        # TX pin to DFPlayer Rx
AUDIO_RX_PIN = 18        # RX pin to DFPlayer Tx
AUDIO_BAUDRATE = 9600

# Auxiliary Device Settings
AUX_DEVICES_CONFIG = {
    "fogger": {"pin": 7, "type": "digital"},
    "solenoid_valve": {"pin": 8, "type": "digital"}
}

# --- Show Settings ---
AVAILABLE_SEQUENCES = [
    "sequence_demo",
    "sequence_rainbow"
]
