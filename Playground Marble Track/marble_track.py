from machine import Pin, PWM, time_pulse_us, Timer
import time
import neopixel
import asyncio
from now import Now

class RangeGateController:
    def __init__(self, trigger_pin=19, echo_pin=17, neo_pin=0, servo_pin=18, start_pin=1, start_servo=2, target_dist=100):
        # Initialize pins for ultrasonic sensor
        self.trigger_pin = Pin(trigger_pin, Pin.OUT)
        self.echo_pin = Pin(echo_pin, Pin.IN)

        # Initialize start gate pins
        self.start_button = Pin(start_pin, Pin.IN, Pin.PULL_UP)
        self.long_press_duration = 3000
        self.pressed = False
        self.press_start_time = 0

        self.start_servo = PWM(Pin(start_servo))
        self.start_servo.freq(50)

        # Initialize LED strip
        self.num_leds = 45
        self.np = neopixel.NeoPixel(Pin(neo_pin), self.num_leds)

        # Initialize servo motor
        self.servo_pwm = PWM(Pin(servo_pin))
        self.servo_pwm.freq(50)

        # Distance and LED configuration
        self.target_dist = target_dist
        self.threshold = 5
        self.min_dist = 3
        self.max_dist = target_dist * 2

        # State variables
        self.on_target = False
        self.gate_closed = True
        self.start_closed = True
        self.distance = None
        self.on = False

        # Initialize communication
        self.n = Now(self.now_callback)
        self.n.connect()

        # Set initial states
        self.close_gate()
        self.close_start()
        self.clear_leds()

        # Start asynchronous tasks
        asyncio.create_task(self.update_distance())
        asyncio.create_task(self.run())
        asyncio.create_task(self.start_button_handler())
        asyncio.get_event_loop().run_forever()

    def now_callback(self, msg, mac):
        # Handle incoming messages
        if msg == b'marblestart' and not self.on:
            self.start_puzzle()

    def measure_distance(self):
        # Measure distance using the ultrasonic sensor
        self.trigger_pin.value(0)
        time.sleep_us(2)
        self.trigger_pin.value(1)
        time.sleep_us(10)
        self.trigger_pin.value(0)

        duration = time_pulse_us(self.echo_pin, 1, 30000)  # Timeout after 30 ms

        if duration > 0:
            return (duration * 0.0343) / 2  # Convert duration to distance in cm
        else:
            return None

    async def update_distance(self):
        # Periodically measure and update the distance
        while True:
            if self.on:
                self.distance = self.measure_distance()
                await asyncio.sleep(0.2)
            else:
                await asyncio.sleep(0.5)

    def set_led(self, index, rgb):
        # Set a single LED color
        self.np[index] = rgb
        self.np.write()

    def clear_leds(self):
        # Turn off all LEDs
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()

    def set_servo_angle(self, angle):
        # Set servo angle for the gate
        min_duty = 1638  # 0.5 ms pulse
        max_duty = 8192  # 2.5 ms pulse
        duty = min_duty + int((max_duty - min_duty) * (angle / 180))
        self.servo_pwm.duty_u16(duty)

    def set_start_angle(self, angle):
        # Set servo angle for the start gate
        min_duty = 1638
        max_duty = 8192
        duty = min_duty + int((max_duty - min_duty) * (angle / 180))
        self.start_servo.duty_u16(duty)

    def close_gate(self):
        # Close the main gate
        self.set_servo_angle(0)
        self.gate_closed = True

    def open_gate(self):
        # Open the main gate
        self.set_servo_angle(85)
        self.gate_closed = False

    def close_start(self):
        # Close the start gate
        self.set_start_angle(5)
        self.start_closed = True

    def open_start(self):
        # Open the start gate
        self.set_start_angle(90)
        self.start_open = False

    async def expand_leds(self):
        # Expand LED colors outward from the center
        center = 22
        self.clear_leds()
        self.set_led(center, (0, 255, 0))
        for i in range(1, 22):
            await asyncio.sleep(0.05)
            if not self.on_target:
                return
            self.set_led(center + i, (255, 0, 0))
            self.set_led(center - i, (255, 0, 0))
        if i == 21 and self.on_target:
            self.completed()

    async def run(self):
        # Main loop for handling distance and LEDs
        while True:
            if self.on:
                if self.distance is not None:
                    dist = max(self.min_dist, self.distance)

                    if dist < self.max_dist:
                        normalized = (dist - self.min_dist) / (self.max_dist - self.min_dist)
                        led_index = round(normalized * (self.num_leds - 1))

                        if self.target_dist - self.threshold < dist < self.target_dist + self.threshold:
                            if not self.on_target:
                                asyncio.create_task(self.expand_leds())
                                self.on_target = True
                        else:
                            self.on_target = False
                            self.clear_leds()
                            self.set_led(led_index, (255, 0, 0))
                    else:
                        self.on_target = False
                        self.clear_leds()
                else:
                    print("Out of range")
                    self.clear_leds()

                await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.5)

    def start_puzzle(self):
        # Start the puzzle
        self.close_gate()
        self.on = True

    async def start_button_handler(self):
        # Handle button presses
        while True:
            if self.start_button.value() == 0:
                if not self.pressed:
                    self.pressed = True
                    print('pressed')
                    self.press_start_time = time.ticks_ms()
            else:
                if self.pressed:
                    self.pressed = False
                    press_length = time.ticks_diff(time.ticks_ms(), self.press_start_time)
                    print(press_length)
                    if press_length > self.long_press_duration:
                        self.long_press()
                    else:
                        self.short_press()
            await asyncio.sleep(0.2)

    def short_press(self):
        # Handle short press to start the puzzle
        if not self.on:
            self.open_start()
            print('start')
            time.sleep(1)
            self.close_start()
            time.sleep(5)
            self.on = True

    def long_press(self):
        # Handle long press to reset the puzzle
        print('reset')
        if self.on:
            self.on = False
            self.clear_leds()
            self.open_gate()
            self.n.publish(b'reset')
            time.sleep(3)
            self.close_gate()
            self.close_start()

    def completed(self):
        # Handle puzzle completion
        self.open_gate()
        self.clear_leds()
        self.n.publish(b'1complete')
        time.sleep(2)
        self.close_gate()
        self.on = False

controller = RangeGateController()
