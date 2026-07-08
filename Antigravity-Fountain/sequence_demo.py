# Show Sequence: Demo Wave Show

import math

async def run_sequence(devices, seq):
    print("DEMO SHOW: Starting...")
    
    # Trigger audio track 1 with 80% volume and 100% tempo
    devices.play_audio(track_id=1, volume=80, tempo=100)
    
    # Turn on fogger at start
    devices.control_aux("fogger", "ON")
    
    # Simple color list for cycles
    colors = [
        (255, 0, 0),   # Red
        (0, 255, 0),   # Green
        (0, 0, 255),   # Blue
        (255, 255, 0), # Yellow
        (255, 0, 255), # Magenta
        (0, 255, 255)  # Cyan
    ]
    
    t = 0.0
    color_index = 0
    
    while True:
        # 1. Animate Pump Motors (Sine wave phase-shifted by 120 degrees / 2*pi/3)
        for i in range(3):
            phase = i * (2 * math.pi / 3)
            # Calculate motor speed between 20% and 100%
            speed = int(60 + 40 * math.sin(t + phase))
            devices.set_motor(i, speed)
            
        # 2. Cycle NeoPixel colors periodically (every step cycles them slightly)
        pixel_color = colors[color_index]
        for p in range(3):
            # Phase shift pixel indices for a moving color trail
            shift_idx = (color_index + p) % len(colors)
            r, g, b = colors[shift_idx]
            # Dim the pixels slightly for simulation (50% brightness)
            devices.set_led(p, int(r * 0.5), int(g * 0.5), int(b * 0.5), flush=False)
        devices.leds.show()  # Flush LED updates
        
        # 3. Periodically cycle auxiliary devices
        if int(t) % 10 == 0:
            devices.control_aux("solenoid_valve", "ON")
        elif int(t) % 10 == 5:
            devices.control_aux("solenoid_valve", "OFF")
            
        # Log status every few ticks
        if int(t * 10) % 20 == 0:
            print("DEMO SHOW: Time={:.1f}s | Pump Speeds=[{}, {}, {}]".format(
                t, 
                devices.motors[0].speed, 
                devices.motors[1].speed, 
                devices.motors[2].speed
            ))
            
        # Cooperative sleep (yielding to Blynk and checking for pause/stop)
        await seq.sleep(0.1)
        
        # Increment time and cycle color index
        t += 0.1
        if int(t * 10) % 30 == 0:
            color_index = (color_index + 1) % len(colors)
