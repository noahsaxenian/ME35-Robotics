from machine import I2C, Pin
import struct
import time

class Acceleration():
    def __init__(self, scl, sda, addr = 0x62):
        self.addr = addr
        self.i2c = I2C(1,scl=scl, sda=sda, freq=100000) 
        self.connected = False
        if self.is_connected():
            print('I2C connected')
            self.write_byte(0x11,0) #start data stream

    def is_connected(self):
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
        # Shift the byte right by `bit_position` and mask with 1 to get the value of that bit
        return (byte_value >> bit_position) & 1
        
    def read_taps(self):
        buffer = self.i2c.readfrom_mem(self.addr, 0x09, 1)
        # Convert the byte to an integer
        byte_value = struct.unpack('B', buffer)[0]  # buffer is a bytes object, we get the first (and only) byte
        s_tap = self.get_bit_value(byte_value, 5) == 1
        d_tap = self.get_bit_value(byte_value, 4) == 1

        return s_tap, d_tap
            
    def enable_tap_interrupt(self):
        self.write_byte(0x16, 0x20)
        self.write_byte(0x19, 0x20)
            
    def orientation(self):
        buffer = self.i2c.readfrom_mem(self.addr, 0x0C, 1)
        byte_value = struct.unpack('B', buffer)[0]
        z = (byte_value >> 6) & 1
        xy = (byte_value >> 4) & 0b11
        
        print(f' z: {bin(z)}  xy: {bin(xy)}')