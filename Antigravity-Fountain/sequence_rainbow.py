# Show Sequence: Rainbow Pulse Show

import math

async def run_sequence(devices, seq):
    print("RAINBOW PULSE SHOW: Starting...")
    
    # Trigger audio track 2 (High energy) with 90% volume and 120% tempo
    devices.play_audio(track_id=2, volume=90, tempo=120)
    
    # Fogger off, Solenoid valve off initially
    devices.control_aux("fogger", "OFF")
    devices.control_aux("solenoid_valve", "OFF")
    
    # Rainbow color function (Wheel)
    def get_rainbow_color(pos):
        pos = int(pos) % 255
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    t = 0.0
    while True:
        # 1. Pulsate all motors in unison (synchronized surge)
        # Pulse speed goes from 30% to 90% and back
        surge_speed = int(60 + 30 * math.sin(2 * t))
        for i in range(3):
            devices.set_motor(i, surge_speed)
            
        # 2. Smooth Rainbow cycle on the NeoPixel LEDs
        for p in range(3):
            # Each pixel gets a offset value
            pixel_pos = (t * 50 + p * 85) % 255
            r, g, b = get_rainbow_color(pixel_pos)
            devices.set_led(p, int(r * 0.4), int(g * 0.4), int(b * 0.4), flush=False)
        devices.leds.show()  # Flush LED updates
        
        # 3. Synchronized Aux pulses
        if int(t * 2) % 4 == 0:
            devices.control_aux("fogger", "ON")
            devices.control_aux("solenoid_valve", "ON")
        elif int(t * 2) % 4 == 2:
            devices.control_aux("fogger", "OFF")
            devices.control_aux("solenoid_valve", "OFF")
            
        # Log status every few seconds
        if int(t * 10) % 20 == 0:
            print("RAINBOW PULSE: Time={:.1f}s | Unison Pump Speed={} | LED0={}".format(
                t, 
                surge_speed, 
                devices.leds.np[0]
            ))
            
        # Cooperative sleep
        await seq.sleep(0.05)  # Faster updates (20Hz)
        t += 0.05
