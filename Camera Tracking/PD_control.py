import time
import machine
import sensor
from machine import Pin, PWM

# Setup camera
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)  # must turn this off to prevent image washout...
sensor.set_auto_whitebal(False)  # must turn this off to prevent image washout...

# Camera intrinsic parameters
f_x = (2.8 / 3.984) * 160  # Focal length in pixels
f_y = (2.8 / 2.952) * 120  # Focal length in pixels
c_x = 160 * 0.5  # Principal point x
c_y = 120 * 0.5  # Principal point y

# Motor control setup
pwm2 = PWM(Pin(2, Pin.OUT))
pwm3 = PWM(Pin(3, Pin.OUT))
pwm2.freq(1000)  # PWM frequency in Hz
pwm3.freq(1000)

# PD controller gains
kp = 1.0  # Proportional gain
kd = 0.1  # Derivative gain

desired_x = 0  # Desired position, 0 is center

dead_zone = 0  # dead zone threshold, tune for motor, 0 does nothing

# Variables to track previous error for the derivative term
previous_error = 0
previous_time = time.ticks_ms()

while True:
    # Initialize variables
    x = None
    found_tag = 0
    img = sensor.snapshot()

    # Look for AprilTags
    for tag in img.find_apriltags(fx=f_x, fy=f_y, cx=c_x, cy=c_y):
        img.draw_rectangle(tag.rect(), color=(255, 0, 0))
        img.draw_cross(tag.cx(), tag.cy(), color=(0, 255, 0))
        x = tag.x_translation  # x position of the tag
        found_tag = 1

    # PD control
    if found_tag:
        error = x - desired_x  # Calculate error (difference from the center)
        current_time = time.ticks_ms()
        delta_time = time.ticks_diff(current_time, previous_time) / 1000.0  # Convert to seconds

        # Calculate derivative of the error (rate of change)
        if delta_time > 0:
            derivative = (error - previous_error) / delta_time
        else:
            derivative = 0

        # PD control signal
        control_signal = (kp * error) + (kd * derivative)

        # Update previous error and time
        previous_error = error
        previous_time = current_time

        pwm_value = abs(int(control_signal * 1023)) # scale to pwm range
        pwm_value += dead_zone # shift to avoid dead zone
        pwm_value = min(pwm_value, 1023) # keep within range

        # Set motor direction and PWM based on control signal
        if control_signal > 0:
            # Forward motion
            pwm2.duty(pwm_value)
            pwm3.duty(0)  # Reverse pin off
        else:
            # Reverse motion
            pwm3.duty(pwm_value)
            pwm2.duty(0)  # Forward pin off
    else:
        # Stop the motor if no tag is found
        pwm2.duty(0)
        pwm3.duty(0)

    time.sleep_ms(10)
