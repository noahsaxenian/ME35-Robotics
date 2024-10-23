from machine import Pin, I2C, ADC, Timer, UART
import ssd1306
import time
from wifi import *
from mqtt import MQTTClient


class MIDI_Display:
    
    def __init__(self, i2c_scl_pin=7, i2c_sda_pin=6, oled_width=128, oled_height=64, mqtt_topic='noah_midi'):
        
        # Initialize I2C interface for the SSD1306 OLED display
        self.i2c = I2C(0, scl=Pin(i2c_scl_pin), sda=Pin(i2c_sda_pin))  # Adjust pins as needed
        self.oled = ssd1306.SSD1306_I2C(oled_width, oled_height, self.i2c)
        self.oled.fill(0)
        self.oled.show()
        
        self.uart = UART(1, baudrate=9600, tx=Pin(21), rx=Pin(20))
        
        self.chords = ['C7', 'CM7', 'C-7', 'C#7', 'C#M7', 'C#-7', 'D7', 'DM7', 'D-7', 'D#7', 'D#M7', 'D#-7', 'E7', 'EM7', 'E-7', 'F7', 'FM7', 'F-7', 'F#7', 'F#M7', 'F#-7', 'G7', 'GM7', 'G-7', 'G#7', 'G#M7', 'G#-7', 'A7', 'AM7', 'A-7', 'A#7', 'A#M7', 'A#-7', 'B7', 'BM7', 'B-7']
        self.selected_chords = [1,8,14,16,21,27]
        self.selector = 0
        self.selected = False
        
        # Configure buttons with internal pull-ups and attach interrupts
        self.button_down = Pin(10, Pin.IN, Pin.PULL_UP)
        self.button_select = Pin(9, Pin.IN, Pin.PULL_UP)
        self.button_up = Pin(8, Pin.IN, Pin.PULL_UP)

        # Attach interrupts to detect button presses (falling edge means button pressed)
        self.button_down.irq(trigger=Pin.IRQ_FALLING, handler=self.down_pressed)
        self.button_select.irq(trigger=Pin.IRQ_FALLING, handler=self.select_pressed)
        self.button_up.irq(trigger=Pin.IRQ_FALLING, handler=self.up_pressed)
        
        self.pot = ADC(Pin(3))
        self.pot.atten(ADC.ATTN_11DB) # the pin expects a voltage range up to 3.3V
        self.volume = self.pot.read() / 4095
        
        # timer for sending updates to pico
        self.timer = Timer(0)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self.timer_callback)
        
        #self.topic_pub = mqtt_topic
        #self.initialize_mqtt()
        self.update()
        
    def initialize_mqtt(self):
        # connect MQTT client and subscribe to topic
        mqtt_broker = 'broker.emqx.io' 
        port = 1883

        self.client = MQTTClient('display', mqtt_broker , port, keepalive=60)
        self.client.connect()
        print('Connected to %s MQTT broker' % (mqtt_broker))
        
    
    def timer_callback(self, timer):
        # send updates to pico
        self.get_volume()
        msg = ''
        for chord in self.selected_chords:
            msg += str(chord) + ','
        msg += str(self.volume)
                
        # Manually pad the message to 30 characters
        if len(msg) < 30:
            msg = msg + ' ' * (30 - len(msg))  # Append spaces to reach 30 characters
        #print(msg)
        self.uart.write(msg.encode('ascii'))
        #self.client.publish(self.topic_pub.encode(), msg.encode())
    
                
    def down_pressed(self, pin):
        # down button callback
        if self.selected:
            self.selected_chords[self.selector-1] = (self.selected_chords[self.selector-1] - 1) % len(self.chords)
        else:
            self.selector = (self.selector - 1) % 7
        self.update()
        time.sleep(0.1)

    def select_pressed(self, pin):
        # select button callback
        self.selected = not self.selected
        self.update()
        time.sleep(0.2)

    def up_pressed(self, pin):
        # up button callback
        if self.selected:
            self.selected_chords[self.selector-1] = (self.selected_chords[self.selector-1] + 1) % len(self.chords)
        else:
            self.selector = (self.selector + 1) % 7
        self.update()
        time.sleep(0.1)

    def draw_chords(self):
        # draw the chord names and button numbers
        if self.selected: color = 0
        else: color = 1
        for i in range(6):
            name = self.chords[self.selected_chords[i]]
            m = i % 3
            if len(name) == 2:
                x_pos = 40*m+15
            elif len(name) == 3:
                x_pos = 40*m+11
            else:
                x_pos = 40*m+7
            if i < 3:
                y_pos = 10
            else:
                y_pos = 40
            if self.selected and self.selector == i+1:
                color = 0
            else: color = 1
            self.oled.text(name, x_pos, y_pos, color)
            self.oled.text(f'{i+1}', 40*m+20, y_pos+10, color)

    def draw_selector(self):
        # draw the selector box in correct position
        pos = self.selector
        # Position 1-6, 0 clears
        for i in range(6):
            if i < 3:
                self.oled.rect(i*40+3, 5, 40, 26, 0, True)
            else:
                self.oled.rect((i-3)*40+3, 35, 40, 26, 0, True)
        if pos != 0 and pos <= 6:
            pos = pos-1
            if pos < 3:
                self.oled.rect(pos*40+3, 5, 40, 26, 1, self.selected)
            else:
                self.oled.rect((pos-3)*40+3, 35, 40, 26, 1, self.selected)
                
    def get_volume(self):
        self.volume = round(self.pot.read() / 4095, 1)
        #print(self.volume)
        
    def update(self):
        self.draw_selector()
        self.draw_chords()
        self.oled.show()

# Example usage
#connect_wifi()
display = MIDI_Display()