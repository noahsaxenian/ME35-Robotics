import time
from mqtt import MQTTClient
import network
from secrets import mysecrets
import urequests
import asyncio
from machine import Pin, PWM
import neopixel
import random

class Nightlight():
    
    def __init__(self):
        self.on = False
        
        self.led = PWM(Pin('GPIO0', Pin.OUT))
        self.led.freq(50)
        self.led.duty_u16(0)
        
        self.buzzer = PWM(Pin('GPIO18', Pin.OUT))
        self.buzzer.freq(220)
        self.buzzer.duty_u16(0)
        
        self.button = Pin('GPIO20', Pin.IN, machine.Pin.PULL_UP)
        self.button.irq(trigger=Pin.IRQ_FALLING, handler=self.button_press)
        
        self.neo = neopixel.NeoPixel(Pin(28),1)
        self.neo[0] = (0,0,0)
        self.neo.write()
        
        self.connect()
        asyncio.run(self.breath())
        
    def connect(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(mysecrets['SSID'], mysecrets['key'])
        while wlan.ifconfig()[0] == '0.0.0.0':
            print('.', end=' ')
            time.sleep(1)
        return wlan.ifconfig()
    
    def start_mqtt(self):
        mqtt_broker = 'broker.hivemq.com' 
        port = 1883
        topic_sub = 'nightlight/#'       # this reads anything sent to ME35
        topic_pub = 'nightlight/tell'


        def callback(topic, msg):
            print((topic.decode(), msg.decode()))

        client = MQTTClient('Noah', mqtt_broker , port, keepalive=60)
        client.connect()
        print('Connected to %s MQTT broker' % (mqtt_broker))
        client.set_callback(callback)          # set the callback if anything is read
        client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics

        msg = 'this is a test'
        i = 0
        while True:
            i+=1
            if i %5 == 0:
                print('publishing')
                client.publish(topic_pub.encode(),msg.encode())
            client.check_msg()
            time.sleep(1)
            
    async def breath(self):
        while self.on:
            for i in range(0,65535,500):
                self.led.duty_u16(i)     #  u16 means unsighed 16 bit integer (0-65535)
                await asyncio.sleep_ms(10)
            for i in range(65535,0,-500):
                self.led.duty_u16(i)     #  u16 means unsighed 16 bit integer (0-65535)
                await asyncio.sleep_ms(10)
                
    async def beep(self):
        self.buzzer.duty_u16(500)
        await asyncio.sleep(1)
        self.buzzer.duty_u16(0)
        
    def update_neopixel(self):
        if self.on:
            r = random.randint(0, 50)
            g = random.randint(0, 50)
            b = random.randint(0, 50)
            self.neo[0] = (r,g,b)
        else:
            self.neo[0] = (0,0,0)
        self.neo.write()
        
    def button_press(self, state):
        self.update_neopixel()
        if self.on:
            asyncio.run(self.beep())
            
    def toggle_state(self):
        self.on = not self.on
        if self.on:
            asyncio.run(self.breath())
        self.update_neopixel()
            
test = Nightlight()
test.toggle_state()
