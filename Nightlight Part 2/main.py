from MSA311 import Acceleration
import asyncio
from machine import Pin, PWM
import time
import network
from secrets import mysecrets
import urequests
from mqtt import MQTTClient
import neopixel
import random


class Nightlight():
    
    def __init__(self):
                
        # on/off flag
        self.on = True
        self.button_toggle = False
        
        # connect
        self.connect_wifi(2)
        self.start_mqtt()
        
        # setup acccelerometer
        scl = Pin('GPIO27', Pin.OUT)
        sda = Pin('GPIO26', Pin.OUT)
        self.accel = Acceleration(scl, sda)
        self.accel.enable_tap_interrupt()
        
        # interrupt from accelerometer
        self.int = Pin(10, Pin.IN)
        self.int.irq(trigger=Pin.IRQ_FALLING, handler=self.on_tap)
        
        self.button = Pin(9, Pin.IN, Pin.PULL_UP)
        self.button.irq(trigger=Pin.IRQ_FALLING, handler=self.button_press)

        # setup LED
        self.led = Pin(6, Pin.OUT)
        self.led.off()
        
        # setup servo
        self.servo = PWM(Pin(22))
        self.servo.freq(50)
        
        # setup neopixel
        self.neo = neopixel.NeoPixel(Pin(28),1)
        self.neo[0] = (0,0,0)
        self.neo.write()
        
        # startup asyncio
        asyncio.create_task(self.check_messages())
        asyncio.create_task(self.pan_servo())
        asyncio.get_event_loop().run_forever()
        
    def connect_wifi(self, index=2):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(mysecrets[index]['SSID'], mysecrets[index]['key'])
        while wlan.ifconfig()[0] == '0.0.0.0':
            print('.', end=' ')
            time.sleep(1)
        print('wifi connected')
        return wlan.ifconfig()
    
    def start_mqtt(self):
        # connect MQTT client and subscribe to topic
        mqtt_broker = 'broker.hivemq.com' 
        port = 1883
        topic_sub = 'ME35-24/Kaisnightlight'

        def callback(topic, msg):
            # callback checks if topic and message are correct to turn on/off
            if topic.decode() == topic_sub:
                if msg.decode() == 'on':
                    self.on = True
                    print('on')
                if msg.decode() == 'off':
                    self.on = False
                    self.update_neopixel()
                    print('off')

        self.client = MQTTClient('Noah', mqtt_broker , port, keepalive=0)
        self.client.connect()
        print('Connected to %s MQTT broker' % (mqtt_broker))
        self.client.set_callback(callback)          # set the callback if anything is read
        self.client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics
        
    async def check_messages(self):
        # constantly check for new MQTT messages
        while True:
            self.client.check_msg()
            await asyncio.sleep(0.5)
    
    def button_press(self, p):
        print('button')
        self.button_toggle = not self.button_toggle

    def on_tap(self, p):
        print('tap')
        self.update_neopixel()
        
    def update_neopixel(self):
        # set neopixel to a random color if nightlight is on
        # otherwise make sure neopixel is off
        if self.on:
            colors = [
                (255, 0, 0),     # Pure Red
                (0, 255, 0),     # Pure Green
                (0, 0, 255),     # Pure Blue
                (255, 255, 255), # White
                (0, 255, 255),   # Cyan
                (255, 0, 255),   # Magenta
                (255, 255, 0),   # Yellow
                (255, 165, 0),   # Orange
                (255, 20, 147),  # Pink
                (128, 0, 128),   # Purple
                (0, 128, 128),   # Teal
                (173, 216, 230), # Light Blue
                (50, 205, 50),   # Lime
                (255, 215, 0),   # Gold
                (64, 224, 208),  # Turquoise
                (230, 230, 250), # Lavender
                (255, 127, 80),  # Coral
                (250, 128, 114), # Salmon
                (0, 191, 255),   # Deep Sky Blue
                (148, 0, 211)    # Dark Violet
                ]
            self.neo[0] = random.choice(colors) # pick a random color
        else:
            self.neo[0] = (0,0,0)
        self.neo.write()
            
    async def pan_servo(self):
        MIN = 3277
        MAX = 6553
        while True:
            if self.on and self.button_toggle:
                self.led.on()
                for i in range(MIN, MAX, 20):
                    self.servo.duty_u16(i)
                    await asyncio.sleep_ms(10)
                for i in range(MAX, MIN, -20):
                    self.servo.duty_u16(i)
                    await asyncio.sleep_ms(10)
            else:
                self.led.off()
                await asyncio.sleep(0.5)
        
n = Nightlight()
    
