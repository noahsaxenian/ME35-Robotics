import time
from mqtt import MQTTClient
from wifi import *
from machine import Pin, PWM

connect_wifi()  # connect to wifi using  custom wifi module

mqtt_broker = 'broker.hivemq.com' 
port = 1883
topic_sub = 'ME35-24/carstartstop'

run = False     # flag for start/stop

def callback(topic, msg):
    # callback for when a new MQTT message is recieved on the topic
    global run
    string = msg.decode()
    if string == "run":
        run = True
    elif string == "stop":
        run = False          

client = MQTTClient('startstop', mqtt_broker , port)
client.connect()
print('Connected to %s MQTT broker' % (mqtt_broker))
client.set_callback(callback)          # set the callback if anything is read
client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics
    
# setup pin to communicate with other Pico
pin2 = Pin(2, Pin.OUT)
pin2.value(0)

# loop forever
while True:
    client.check_msg()
    
    if run:
        pin2.value(1)
    else:
        pin2.value(0)
        
    time.sleep_ms(100)