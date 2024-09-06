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

        self.breath_task = None
        
        self.connect()
        self.start_mqtt()

                # Start the event loop
        asyncio.create_task(self.check_messages())  # Schedule the MQTT message checking
        asyncio.get_event_loop().run_forever()      # Keep the event loop running
        
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
        topic_sub = 'nightlight/switch'

        def callback(topic, msg):
            print((topic.decode(), msg.decode()))
            if topic.decode() == 'nightlight/switch' and msg.decode() == 'toggle':
                self.toggle_state()

        self.client = MQTTClient('Noah', mqtt_broker , port, keepalive=60)
        self.client.connect()
        print('Connected to %s MQTT broker' % (mqtt_broker))
        self.client.set_callback(callback)          # set the callback if anything is read
        self.client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics

    async def check_messages(self):
        while True:
            self.client.check_msg()
            await asyncio.sleep(1)
            
    async def breath(self):
        try:
            while True:
                if self.on:
                    for i in range(0, 65535, 500):
                        self.led.duty_u16(i)
                        await asyncio.sleep_ms(20)
                    for i in range(65535, 0, -500):
                        self.led.duty_u16(i)
                        await asyncio.sleep_ms(20)
                else:
                    self.led.duty_u16(0)
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self.led.duty_u16(0)  # Ensure the LED turns off when canceled
            print("Breath task canceled")
            return
                
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
            asyncio.create_task(self.beep())
            
    def toggle_state(self):
        self.on = not self.on
        self.update_neopixel()
        if self.on:
            self.breath_task = asyncio.create_task(self.breath())
        else:
            self.breath_task.cancel()
            
night = Nightlight()