import time
from BLE_CEEO import Yell
from machine import Pin, UART
from wifi import *
from mqtt import MQTTClient
import asyncio

# Mapping of note names to MIDI note numbers
notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
chords = ['C7', 'CM7', 'C-7', 'C#7', 'C#M7', 'C#-7', 'D7', 'DM7', 'D-7', 'D#7', 'D#M7', 'D#-7', 'E7', 'EM7', 'E-7', 'F7', 'FM7', 'F-7', 'F#7', 'F#M7', 'F#-7', 'G7', 'GM7', 'G-7', 'G#7', 'G#M7', 'G#-7', 'A7', 'AM7', 'A-7', 'A#7', 'A#M7', 'A#-7', 'B7', 'BM7', 'B-7']

# MIDI commands
NoteOn = 0x90
NoteOff = 0x80
StopNotes = 123
SetInstrument = 0xC0
Reset = 0xFF

class MidiController:
    def __init__(self, name='midi_keys', mqtt_topic='noah_midi'):
        
        # Initialize buttons on pins 16-21
        self.buttons = [Pin(i, Pin.IN, Pin.PULL_UP) for i in range(10, 16)]
        
        # Initialize indicator LEDs
        self.uart_led = Pin(20, Pin.OUT)
        self.uart_led.value(0)
        self.ble_led = Pin(21, Pin.OUT)
        self.ble_led.value(0)

        # Map buttons to notes (customize as needed)
        self.button_chords = ['CM7', 'D-7', 'E-7', 'FM7', 'G7', 'A-7']  # Map to notes
        self.last_button_values = [1, 1, 1, 1, 1, 1]
        
        self.volume = 1    # volume multiplier
        
        # Setup multiplexer control pins (S0-S3)
        self.s0 = Pin(0, Pin.OUT)
        self.s1 = Pin(1, Pin.OUT)
        self.s2 = Pin(2, Pin.OUT)
        self.s3 = Pin(3, Pin.OUT)
        
        # mappings from key index to note name and octave
        self.key_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B', 'C']
        self.key_octaves = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4]
        
        self.key = machine.ADC(26) # analog input from multiplexer
        self.last_volumes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # last volume from each key
        
        self.uart = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9))    # setup uart communication
        
        #self.topic_sub = mqtt_topic
        #self.initialize_mqtt()
        
        # Set up the BLE connection for MIDI
        self.ble = Yell(name, verbose=True, type='midi')
        self.ble.connect_up()
        
        # startup asyncio tasks and keep running
        asyncio.create_task(self.check_uart())
        asyncio.create_task(self.check_ble())
        asyncio.create_task(self.check_buttons())
        asyncio.create_task(self.check_all_keys())
        asyncio.get_event_loop().run_forever()
        
    def mqtt_callback(self, topic, msg):
        # if mqtt worked
        string = msg.decode()
        print(string) #edit this to decode msg
        
    async def check_uart(self):
        # read data from UART connection
        while True:
            if self.uart.any():
                # Read the data
                received_data = self.uart.read(30) # expecting 30 byte chunks
                await asyncio.sleep_ms(1)
                try:
                    # Attempt to decode the data
                    msg = received_data.decode()
                    print("Received from ESP32:", msg)
                    # Split the string by commas
                    values = msg.split(',')
                    if len(values) == 7: # confirm that data is in expected format - 7 comma separated values
                        self.uart_led.value(1) # indicate good reading
                        # Convert the first 6 values to integers
                        int_values = list(map(int, values[:-1]))
                        for i in range(6):
                            self.button_chords[i] = chords[int_values[i]] # map interger indices to chord names
                        # Convert the last value to float
                        self.volume = float(values[-1][:3]) # volume multiplier from potentiometer
                    else: self.uard_led.value(0) # indicate bad reading
                except Exception as e:
                    print("Received data could not be decoded:", e)
                    self.uart_led.value(0)      # indicate bad reading
            await asyncio.sleep(0.3)
            
    def initialize_mqtt(self):
        # connect MQTT client and subscribe to topic
        mqtt_broker = 'broker.emqx.io' 
        port = 1883

        self.client = MQTTClient('controller', mqtt_broker , port, keepalive=60)
        self.client.connect()
        print('Connected to %s MQTT broker' % (mqtt_broker))
        
        self.client.set_callback(self.mqtt_callback)   # set the callback if anything is read
        self.client.subscribe(self.topic_sub.encode())
        
    def send_midi(self, note_num, velocity, cmd):
        # send a note over bluetooth midi
        timestamp_ms = time.ticks_ms()
        tsM = (timestamp_ms >> 7 & 0b111111) | 0x80
        tsL = 0x80 | (timestamp_ms & 0b1111111)
        
        # Send command for note
        c = cmd | (0x0F & 0)  # Channel is hard-coded as 0
        payload = bytes([tsM, tsL, c, note_num, velocity])
        self.ble.send(payload)

    def play_note(self, note_letter, octave=3, velocity=64, on=True):
        # play a note based on note name
        note_num = notes[note_letter] + 12 * (octave + 2)    # convert letter and octave to midi num
        if on:
            print(f"Playing note: {note_letter}{octave} -> MIDI number: {note_num} -> velocity: {velocity}")
            self.send_midi(note_num, velocity, NoteOn)
        else:
            self.send_midi(note_num, velocity, NoteOff)
        
    def play_chord(self, chord_name, octave=2, velocity=64, on=True):
        # play a chord based on chord name (supports major, minor, dominant)
        chord_type = chord_name[-2] # second to last character should be -, M, or note
        # define intervals from root
        if chord_type == '-':
            intervals = [0, 3, 7, 10] # minor 7 chord
        elif chord_type == 'M':
            intervals = [0, 4, 7, 11] # major 7 chord
        else:
            intervals = [0, 4, 7, 10] # dominant 7 chord
        
        # determine name of root
        if chord_name[1] == '#':
            root_name = chord_name[:2]
        else: root_name = chord_name[0]
        
        # get midi number of root
        root_num = notes[root_name] + 12 * (octave + 2)
        
        # play each note in chord
        for interval in intervals:
            if on:
                self.send_midi(root_num+interval, velocity, NoteOn)
            else:
                self.send_midi(root_num+interval, velocity, NoteOff)
            

    async def check_buttons(self):
        while True:
            # Check the state of each button and trigger note actions
            for i, button in enumerate(self.buttons):
                chord = self.button_chords[i]
                if not button.value():  # Button pressed (assuming active-low)
                    if self.last_button_values[i] == 1:
                        self.play_chord(chord, octave=2, velocity=int(50*self.volume), on=True)
                else:
                    if self.last_button_values[i] == 0:
                        self.play_chord(chord, octave=2, velocity=64, on=False)
                self.last_button_values[i] = button.value()
                await asyncio.sleep_ms(10)
            
    # Function to select a channel on the multiplexer
    def select_channel(self, channel):
        self.s0.value(channel & 1)
        self.s1.value((channel >> 1) & 1)
        self.s2.value((channel >> 2) & 1)
        self.s3.value((channel >> 3) & 1)
    
    async def check_all_keys(self):
        minval = 10000
        maxval = 60000
        while True:
            for i in range(13):
                self.select_channel(i)
                time.sleep_us(10)  # Small delay to settle switching
                reading = self.key.read_u16()  # Read ADC value (0-65535)
                if reading > minval:
                    volume = int((((reading - minval) / (maxval - minval)) * 127))
                    if self.last_volumes[i] == 0:
                        self.play_note(self.key_notes[i], octave=self.key_octaves[i], velocity=volume)
                else:
                    volume = 0
                    if self.last_volumes[i] != 0:
                        self.play_note(self.key_notes[i], octave=self.key_octaves[i], velocity=0, on=False)
                self.last_volumes[i] = volume
                await asyncio.sleep_ms(10)
        
    async def check_ble(self):
        while True:
            if self.ble.is_connected:
                self.ble_led.value(1) # indicate good connection
            else:
                self.ble_led.value(0) # indicate lost connection
            await asyncio.sleep(1)

# Create the controller object and start checking buttons
#connect_wifi()
midi = MidiController()