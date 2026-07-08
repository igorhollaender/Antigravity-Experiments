# Main Control Loop & Blynk Interface for ESP32-S3 Show Sequencer

import uasyncio as asyncio
import network
import time
import machine
import sys
import urequests

import config
import devices
import sequencer
import BlynkLib

# --- Global State Variables ---
selected_sequence = "sequence_demo"  # Default sequence
ota_url = ""                         # URL for OTA sequence downloading

# --- Initialize Hardware Devices ---
print("Initializing devices...")
devices_mgr = devices.DeviceManager()

# Register motors
for idx, pin_num in enumerate(config.MOTOR_PINS):
    devices_mgr.register_motor(idx, pin_num)

# Register LEDs
devices_mgr.register_leds(config.NEOPIXEL_PIN, config.NEOPIXEL_NUM)

# Register Audio
devices_mgr.register_audio(
    tx_pin=config.AUDIO_TX_PIN, 
    rx_pin=config.AUDIO_RX_PIN, 
    baudrate=config.AUDIO_BAUDRATE
)

# Register Aux Devices
for aux_id, dev_cfg in config.AUX_DEVICES_CONFIG.items():
    devices_mgr.register_aux(aux_id, dev_cfg["pin"], dev_cfg["type"])

# Make sure all devices are stopped/black at startup
devices_mgr.stop_all()

# --- Initialize Sequencer Engine ---
seq = sequencer.Sequencer(devices_mgr)

# --- Wi-Fi Connection Manager ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi SSID '{}'...".format(config.WIFI_SSID))
        wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
        # Wait for connection (timeout after 15s)
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > 15:
                print("Wi-Fi Connection Timeout!")
                break
            time.sleep(0.5)
            
    if wlan.isconnected():
        print("Wi-Fi Connected! IP Info:", wlan.ifconfig())
        return True
    return False

# Connect to Wi-Fi before continuing
wifi_connected = connect_wifi()

# --- Initialize Blynk Client ---
print("Initializing Blynk IoT...")
blynk = BlynkLib.Blynk(config.BLYNK_AUTH_TOKEN, insecure=True)

# Register Sequencer status callback to write back to Blynk V3 (status widget)
def blynk_status_callback(status_msg):
    try:
        blynk.virtual_write(3, status_msg)
    except Exception as e:
        print("Failed to write status to Blynk:", e)

seq.set_status_callback(blynk_status_callback)

# --- Blynk Event Handlers ---

@blynk.on("V0")
def v0_select_sequence(value):
    """V0: Select Show Sequence (Dropdown / Menu widget)"""
    global selected_sequence
    if not value or not value[0]:
        return
        
    val = value[0]
    # Check if value is a numeric index (for index-based dropdowns)
    if val.isdigit():
        idx = int(val)
        # Map index to available sequences
        all_sequences = config.AVAILABLE_SEQUENCES + (["ota_sequence"] if "ota_sequence" not in config.AVAILABLE_SEQUENCES else [])
        if 0 <= idx < len(all_sequences):
            selected_sequence = all_sequences[idx]
        else:
            selected_sequence = "sequence_demo"
    else:
        # String value matching
        selected_sequence = val
        
    print("Blynk: Selected sequence updated to: {}".format(selected_sequence))
    seq.update_status("SEL: {}".format(selected_sequence))

@blynk.on("V1")
def v1_play_stop(value):
    """V1: Play / Stop Button (1 = Play, 0 = Stop)"""
    if not value or not value[0]:
        return
    
    cmd = int(value[0])
    if cmd == 1:
        print("Blynk: PLAY command received for '{}'".format(selected_sequence))
        success = seq.play(selected_sequence)
        if not success:
            blynk.virtual_write(1, 0) # Toggle button widget back off on error
    else:
        print("Blynk: STOP command received")
        seq.stop()

@blynk.on("V2")
def v2_pause_resume(value):
    """V2: Pause / Resume Button (1 = Pause/Break, 0 = Continue)"""
    if not value or not value[0]:
        return
        
    cmd = int(value[0])
    if cmd == 1:
        print("Blynk: PAUSE command received")
        seq.pause()
    else:
        print("Blynk: CONTINUE command received")
        seq.resume()

@blynk.on("V4")
def v4_ota_url(value):
    """V4: OTA URL Input (Text Widget)"""
    global ota_url
    if value and value[0]:
        ota_url = value[0]
        print("Blynk: OTA URL updated to: {}".format(ota_url))

@blynk.on("V5")
def v5_trigger_ota(value):
    """V5: Trigger OTA Update Button (1 = Trigger update)"""
    if not value or not value[0]:
        return
        
    cmd = int(value[0])
    if cmd == 1:
        print("Blynk: Triggering OTA sequence download...")
        # Start OTA download task asynchronously so we don't block Blynk connection
        asyncio.create_task(perform_ota_download())

@blynk.on("V6")
def v6_reset_system(value):
    """V6: Reset / Reboot system (1 = Reset)"""
    if not value or not value[0]:
        return
        
    cmd = int(value[0])
    if cmd == 1:
        print("Blynk: Reset command received. Rebooting board...")
        seq.stop()
        seq.update_status("REBOOTING...")
        time.sleep(1)
        machine.reset()

# --- OTA Dynamic Downloader Task ---
async def perform_ota_download():
    global selected_sequence
    
    if not ota_url:
        print("OTA Error: No URL provided in V4")
        seq.update_status("OTA ERR: NO URL")
        blynk.virtual_write(5, 0)
        return
        
    seq.update_status("OTA UPDATING...")
    
    # 1. Stop sequencer if currently playing
    if seq.state in (sequencer.STATE_PLAYING, sequencer.STATE_PAUSED):
        print("OTA: Stopping running show sequence first...")
        seq.stop()
        # Give it a second to shutdown and yield
        await asyncio.sleep(1.0)
        
    print("OTA: Fetching file from {} ...".format(ota_url))
    try:
        # Perform HTTP GET request (yielding control during network wait)
        response = urequests.get(ota_url)
        if response.status_code == 200:
            content = response.text
            response.close()
            
            # Save downloaded text as ota_sequence.py on local flash filesystem
            with open("ota_sequence.py", "w") as f:
                f.write(content)
                
            print("OTA: Successfully saved to 'ota_sequence.py'")
            selected_sequence = "ota_sequence"
            seq.update_status("OTA SUCCESS")
            print("OTA: Auto-selected sequence to 'ota_sequence'")
        else:
            print("OTA Error: Server returned HTTP status {}".format(response.status_code))
            seq.update_status("OTA ERR: HTTP {}".format(response.status_code))
            response.close()
    except Exception as e:
        print("OTA Exception occurred during request:", e)
        seq.update_status("OTA ERR: EXCEPTION")
        
    # Reset Blynk OTA trigger button back to 0
    try:
        blynk.virtual_write(5, 0)
    except:
        pass

# --- Background Task Loops ---

async def blynk_network_task():
    """Background task to run the Blynk keepalive and network loop."""
    print("Starting Blynk connection task...")
    
    # Send initial status
    seq.update_status("ONLINE / IDLE")
    
    while True:
        try:
            # Run the client processing loop
            blynk.run()
        except Exception as e:
            print("Blynk process error:", e)
            
        # Yield to let sequencer and other async tasks run
        # Running at ~50Hz (20ms interval) is responsive and keeps latency low
        await asyncio.sleep(0.02)

async def wifi_monitor_task():
    """Periodically check WiFi health and reconnect if disconnected."""
    wlan = network.WLAN(network.STA_IF)
    while True:
        await asyncio.sleep(10)
        if not wlan.isconnected():
            print("WiFi connection lost! Attempting recovery...")
            connect_wifi()

# --- Main Entry Point ---
async def main():
    print("Antigravity Fountain Sequencer System Starting...")
    
    # Launch concurrent async tasks
    blynk_task = asyncio.create_task(blynk_network_task())
    wifi_task = asyncio.create_task(wifi_monitor_task())
    
    # Keep the main coroutine running
    await asyncio.gather(blynk_task, wifi_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user. Stopping all actuators...")
        devices_mgr.stop_all()
        print("Exit.")
