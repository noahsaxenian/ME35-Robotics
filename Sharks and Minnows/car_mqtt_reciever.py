import time
from mqtt import MQTTClient
from wifi import *
from machine import Pin, PWM



connect_wifi()

mqtt_broker = 'broker.hivemq.com' 
port = 1883
topic_sub = 'ME35-24/#'       # this reads anything sent to ME35

x_pos, y_pos = None, None

def callback(topic, msg):
    global x_pos, y_pos
    #print((topic.decode(), msg.decode()))
    if topic.decode() == 'ME35-24/noah':
        string = msg.decode()
        found_tag, x, y = string.split(',')
        x_pos, y_pos = None, None
        if int(found_tag) == 1:
            x_pos = float(x)
            y_pos = float(y)
            

client = MQTTClient('noah', mqtt_broker , port)
client.connect()
print('Connected to %s MQTT broker' % (mqtt_broker))
client.set_callback(callback)          # set the callback if anything is read
client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics

pwm2 = PWM(Pin(2))  # PWM for forward motion
pwm3 = PWM(Pin(3))  # PWM for backward motion

pwm2.freq(1000)  # Set PWM frequency (1kHz)
pwm3.freq(1000)  # Set PWM frequency (1kHz)

def motor_run(speed):
    speed = int(max(-100, min(100, speed))) # constrain from -100 to 100
    # Set motor to move, speed from -100 to 100
    if speed >= 0:
        pwm3.duty_u16(0)  # Ensure backward pin is off
        pwm2.duty_u16(int(speed * 65535 // 100))  # Apply PWM to pin 2 (forward)
    else:
        pwm2.duty_u16(0)  # Ensure forward pin is off
        pwm3.duty_u16(int(-speed * 65535 // 100))  # Apply PWM to pin 3 (backward)

def motor_stop():
    # Stop the motor
    pwm2.duty_u16(0)  # Stop forward motion
    pwm3.duty_u16(0)  # Stop backward motion

y_min = -4.0
y_max = 3.0
y_avg = (y_min + y_max) / 2
x_min = -3.5
x_max = 4.5
x_avg = (x_min + x_max) / 2

motor_sign = 1 # change this to -1 for other wheel

while True:
    client.check_msg()
    if y_pos:
        # make speed from -100 to 100
        speed = int((max(y_min, min(y_max, y_pos)) - y_avg) * (100/((y_max - y_min)/2)))
        
        turn = -int((max(x_min, min(x_max, x_pos)) - x_avg) * (100/((x_max - x_min)/2)))
        
        #print(speed, turn)
        speed = speed + (motor_sign * turn)
        #motor_run(speed)
        
    else:
        motor_stop()
        
    #print(f'x: {x_pos}, y: {y_pos}')
    time.sleep_ms(50)
