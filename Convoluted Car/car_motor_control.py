import time
from mqtt import MQTTClient
from wifi import *
from machine import Pin, PWM

connect_wifi()  # connect to wifi using  custom wifi module

mqtt_broker = 'broker.hivemq.com' 
port = 1883
topic_sub = 'ME35-24/noahmedha'

# adjust range depending on camera position
y_min = -4.5
y_max = 3.5
y_avg = (y_min + y_max) / 2
x_min = -4.0
x_max = 4.0
x_avg = (x_min + x_max) / 2

x_pos, y_pos = x_avg, y_avg   # set to avg values to keep motors still

def callback(topic, msg):
    # callback for new mqtt message on topic
    global x_pos, y_pos

    # decode the message and update position variables
    string = msg.decode()
    if string[1] == ",":       # confirm correct format coming from camera
        found_tag, x, y = string.split(',')
        x_pos, y_pos = x_avg, y_avg
        if int(found_tag) == 1:
            x_pos = float(x)
            y_pos = float(y)
            

client = MQTTClient('motorcontrol', mqtt_broker , port)
client.connect()
print('Connected to %s MQTT broker' % (mqtt_broker))
client.set_callback(callback)          # set the callback if anything is read
client.subscribe(topic_sub.encode())   # subscribe to a bunch of topics

# Setup PWM control for four pins, two for each motor
pwm2 = PWM(Pin(2))
pwm3 = PWM(Pin(3))
pwm4 = PWM(Pin(4))
pwm5 = PWM(Pin(5))
pwm2.freq(1000)
pwm3.freq(1000)
pwm4.freq(1000)
pwm5.freq(1000)

def motor_run(speed, m1, m2):
    # run motor at specified speed (%), m2 and m2 are pwm pins

    speed = int(max(-100, min(100, speed))) # constrain from -100 to 100
    if speed >= 0:
        m2.duty_u16(0)  # Ensure backward pin is off
        m1.duty_u16(int(speed * 65535 // 100))  # Apply PWM to m1 (forward)
    else:
        m1.duty_u16(0)  # Ensure forward pin is off
        m2.duty_u16(int(-speed * 65535 // 100))  # Apply PWM to m2 (backward)

def motor_stop():
    # Stop both motors
    pwm2.duty_u16(0)
    pwm3.duty_u16(0)
    pwm4.duty_u16(0)
    pwm5.duty_u16(0)
    
pin20 = Pin(20, Pin.IN) # setup pin to detect start/stop
    
while True:
    client.check_msg() # check for new messages
    
    if pin20.value() == 1: # check if should be running
        
        # compute speed and turn from x, y position
        
        # speed ranges from -100 to 100
        speed = -int((max(y_min, min(y_max, y_pos)) - y_avg) * (100/((y_max - y_min)/2)))
        
        # turn ranges from -30 to 30
        turn = int((max(x_min, min(x_max, x_pos)) - x_avg) * (30/((x_max - x_min)/2)))
        
        # alter speed values for each motor to account for turn
        motor_run(speed - turn, pwm2, pwm3)
        motor_run(speed + turn, pwm4, pwm5)
    else:
        motor_stop()
        
    time.sleep_ms(10)

