import network
from secrets2 import mysecrets
import urequests
import time
        
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(mysecrets['SSID'], mysecrets['key'])
    while wlan.ifconfig()[0] == '0.0.0.0':
        print('.', end=' ')
        time.sleep(1)
    return wlan.ifconfig()

connect()