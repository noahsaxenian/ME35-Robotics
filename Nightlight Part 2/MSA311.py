from machine import I2C, Pin
import struct
import time

class Acceleration():
    """custom control for MSA311 accelerometer with I2C"""
    
    def __init__(self, scl, sda, addr = 0x62):
        """initialize I2C and attempt connection"""
        self.addr = addr
        self.i2c = I2C(1,scl=scl, sda=sda, freq=100000) 
        self.connected = False
        if self.is_connected():
            print('I2C connected')
            self.write_byte(0x11,0) #start data stream

    def is_connected(self):
        """scan and confirm connection to proper address"""
        options = self.i2c.scan() 
        #print(options)
        self.connected = self.addr in options
        return self.connected 
            
    def read_accel(self):
        buffer = self.i2c.readfrom_mem(self.addr, 0x02, 6) # read 6 bytes starting at memory address 2
        return struct.unpack('<hhh',buffer)

    def write_byte(self, cmd, value):
        self.i2c.writeto_mem(self.addr, cmd, value.to_bytes(1,'little'))
        
    def get_bit_value(self, byte_value, bit_position):
        # for decoding a specific bit from a byte
        # Shift the byte right by `bit_position` and mask with 1 to get the value of that bit
        return (byte_value >> bit_position) & 1
        
    def read_taps(self):
        """read single and double tap interrupt status"""
        buffer = self.i2c.readfrom_mem(self.addr, 0x09, 1)
        # Convert the byte to an integer
        byte_value = struct.unpack('B', buffer)[0]  # buffer is a bytes object, we get the first (and only) byte
        s_tap = self.get_bit_value(byte_value, 5) == 1
        d_tap = self.get_bit_value(byte_value, 4) == 1

        return s_tap, d_tap
            
    def enable_tap_interrupt(self):
        """enable single tap interrupt on int pin of MSA311"""
        self.write_byte(0x16, 0x20) # enable interrupt
        self.write_byte(0x19, 0x20) # map interrupt to int pin