import time
from Tufts_ble import Sniff, Yell
import neopixel
from machine import Pin, PWM
import asyncio

def leds_by_strength(leds, rssi, thresh):
    n_leds = len(leds)
    #print(rssi)
    num = min(n_leds-int((thresh-rssi) / 5), n_leds)
    #print(num)
    for i in range(n_leds):
        leds[i].off()
    for i in range(num):
        leds[i].on()
        
def flash_red(neo, buz):
    buz.freq(880)
    buz.duty_u16(1000)
    neo[0] = (255, 0, 0)
    neo.write()
    time.sleep(0.2)
    neo[0] = (0, 0, 0)
    neo.write()
    time.sleep(0.2)
    buz.duty_u16(0)
        
def save_results(results):
    # convert to string and save as text file
    with open("zombie_results.txt", "w") as f:
        f.write(str(results))

def main():
    
    leds = [Pin(0, Pin.OUT), Pin(1, Pin.OUT), Pin(2, Pin.OUT), Pin(3, Pin.OUT), Pin(4, Pin.OUT), Pin(5, Pin.OUT)]
    
    buz = PWM(Pin('GPIO18', Pin.OUT))

    neo = neopixel.NeoPixel(Pin(28),1)
    neo[0] = (0, 255, 0)
    neo.write()
    
    tags = [0] * 13
    start_times = [None] * 13
    last_times = [None] * 13
    in_range = [False] * 13  # Track if each tag is currently in range
    just_tagged  = [False] * 13
    c = Sniff('!', verbose=False)
    
    rssi_thresh = -60
    
    alive = True
    zombie = 0
    c.scan(0)  # scans forever 
    while alive:
        latest = c.last
        rssi = c.last_rssi
        print(f'{latest} and rssi: {rssi}')
        if latest:
            leds_by_strength(leds, rssi, rssi_thresh)
            c.last = None  # Clear the flag for the next advertisement
            c.last_rssi = None
            
            if rssi > rssi_thresh:
                # set neopixel blue to warn
                neo[0] = (0, 0, 255)
                neo.write()
                
                t = time.ticks_ms()
                
                tagged = int(latest[1:])
                index = tagged - 1
                
                # If tag is detected for the first time or re-detected after leaving
                if not in_range[index]:
                    print(f"Tag {tagged} re-entered range")
                    in_range[index] = True
                    start_times[index] = t
                    last_times[index] = t
                    just_tagged[index] = False
                    
                else:
                    # Check if still in range (within the 0.5-second time window)
                    if t - last_times[index] < 1000:  # Still within 0.5 seconds
                        last_times[index] = t  # Update the last time
                    else:
                        # If out of range for too long, reset the timers
                        print(f"Tag {tagged} left range")
                        in_range[index] = False
                        just_tagged[index] = False
                        start_times[index] = None
                        last_times[index] = None
                        
                        
                # Check if a valid tag
                if in_range[index] and t - start_times[index] > 3000 and not just_tagged[index]:
                    tags[index] += 1
                    print(f'Tagged by group {tagged}')
                    just_tagged[index] = True
                    flash_red(neo, buz)
                    
                    if tags[index] == 3:
                        print(f'Zombified by {tagged}')
                        zombie = tagged
                        alive = False
                        save_results(tags)
        else:
            # set neopixel green to signify safe
            neo[0] = (0, 255, 0)
            neo.write()
            leds_by_strength(leds, -200, rssi_thresh) # make all leds off
                    
        time.sleep(0.1)
        #print(tags)
        
    c.stop_scan()
    
    #red and buzzer to indicate zombie
    neo[0] = (255, 0, 0)
    neo.write()
    buz.freq(440)
    buz.duty_u16(1000)
    
    button = Pin('GPIO20', Pin.IN)
    
    p = Yell()
    while button.value():
        p.advertise(f'!{zombie}')
        time.sleep(0.1)
        
    #turn everything off
    p.stop_advertising()
    buz.duty_u16(0)
    neo[0] = (0, 0, 0)
    neo.write()
    leds_by_strength(leds, -200, rssi_thresh)
    
main()