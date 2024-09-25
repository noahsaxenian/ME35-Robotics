import time
from Tufts_ble import Sniff, Yell  # Import BLE modules for scanning and advertising
import neopixel  # Library for controlling NeoPixels
from machine import Pin, PWM  # Library for controlling GPIO pins and PWM
import asyncio

# Control LED brightness based on RSSI strength
def leds_by_strength(leds, rssi, thresh):
    n_leds = len(leds)
    # Calculate number of LEDs to turn on based on RSSI and threshold
    num = min(n_leds - int((thresh - rssi) / 5), n_leds)
    
    # Turn all LEDs off initially
    for i in range(n_leds):
        leds[i].off()
        
    # Turn on the appropriate number of LEDs
    for i in range(num):
        leds[i].on()

# Flash the NeoPixel red and trigger the buzzer
def flash_red(neo, buz):
    buz.freq(880)  # Set buzzer frequency to 880Hz
    buz.duty_u16(1000)  # Set buzzer duty cycle to 1000
    neo[0] = (255, 0, 0)  # Set NeoPixel to red
    neo.write()  # Apply color to the NeoPixel
    time.sleep(0.2)  # Wait for 0.2 seconds
    neo[0] = (0, 0, 0)  # Turn off NeoPixel
    neo.write()  # Apply the update
    time.sleep(0.2)  # Wait for 0.2 seconds
    buz.duty_u16(0)  # Turn off the buzzer

# Save the results to a text file
def save_results(results):
    with open("zombie_results.txt", "w") as f:
        f.write(str(results))  # Convert the results to string and write to file

# Main function to handle BLE tracking and interaction
def main():
    # Initialize LEDs on GPIO pins 0 to 5
    leds = [Pin(i, Pin.OUT) for i in range(6)]
    
    # Initialize buzzer on GPIO18
    buz = PWM(Pin('GPIO18', Pin.OUT))
    
    # Initialize NeoPixel on GPIO28
    neo = neopixel.NeoPixel(Pin(28), 1)
    neo[0] = (0, 255, 0)  # Set initial color to green
    neo.write()  # Apply the update
    
    # Initialize tag tracking variables
    tags = [0] * 13
    start_times = [None] * 13
    last_times = [None] * 13
    in_range = [False] * 13  # Track if each tag is currently in range
    just_tagged = [False] * 13  # Track if each tag was recently tagged
    c = Sniff('!', verbose=False)  # BLE sniffer, scanning for advertisements
    
    rssi_thresh = -60  # RSSI threshold for detecting devices
    
    alive = True  # Flag for player's status
    zombie = 0  # ID of the zombie that tags the player
    c.scan(0)  # Start BLE scan indefinitely

    while alive:
        latest = c.last  # Latest advertisement received
        rssi = c.last_rssi  # RSSI of the latest advertisement
        
        # If a new advertisement is received
        if latest:
            leds_by_strength(leds, rssi, rssi_thresh)  # Update LEDs based on RSSI
            c.last, c.last_rssi = None, None  # Reset last advertisement and RSSI
            
            if rssi > rssi_thresh:  # If RSSI is strong enough
                neo[0] = (0, 0, 255)  # Set NeoPixel to blue as a warning
                neo.write()
                
                t = time.ticks_ms()  # Get current time in milliseconds
                tagged = int(latest[1:])  # Extract tag ID from advertisement
                index = tagged - 1  # Adjust tag ID to array index
                
                # If the tag re-enters the range
                if not in_range[index]:
                    print(f"Tag {tagged} re-entered range")
                    in_range[index], start_times[index], last_times[index] = True, t, t
                    just_tagged[index] = False
                
                else:
                    # Check if still in range (within 1 second)
                    if t - last_times[index] < 1000:
                        last_times[index] = t  # Update the last seen time
                    else:
                        # Tag has left the range for too long
                        print(f"Tag {tagged} left range")
                        in_range[index] = False
                        just_tagged[index] = False
                        start_times[index], last_times[index] = None, None
                
                # If the tag has been in range for more than 3 seconds and hasn't been recently tagged
                if in_range[index] and t - start_times[index] > 3000 and not just_tagged[index]:
                    tags[index] += 1  # Increment tag count for this tag
                    print(f'Tagged by group {tagged}')
                    just_tagged[index] = True
                    flash_red(neo, buz)  # Flash red and activate buzzer
                    
                    # If the player is tagged 3 times by the same group, they become a zombie
                    if tags[index] == 3:
                        print(f'Zombified by {tagged}')
                        zombie = tagged
                        alive = False
                        save_results(tags)  # Save the tagging results to file
                        
        else:
            # Set NeoPixel to green to signify the player is safe
            neo[0] = (0, 255, 0)
            neo.write()
            leds_by_strength(leds, -200, rssi_thresh)  # Turn off all LEDs
        
        time.sleep(0.1)  # Wait for 0.1 seconds before the next loop

    c.stop_scan()  # Stop BLE scanning when the player becomes a zombie

    # Set NeoPixel red and activate buzzer to indicate zombification
    neo[0] = (255, 0, 0)
    neo.write()
    buz.freq(440)
    buz.duty_u16(1000)
    
    # Wait for button press to start advertising
    button = Pin('GPIO20', Pin.IN)
    p = Yell()  # Start BLE advertising
    while button.value():
        p.advertise(f'!{zombie}')  # Advertise the zombie's tag ID
        time.sleep(0.1)
    
    # Stop advertising and turn everything off
    p.stop_advertising()
    buz.duty_u16(0)
    neo[0] = (0, 0, 0)
    neo.write()
    leds_by_strength(leds, -200, rssi_thresh)  # Turn off all LEDs

# Start the main function
main()
