import network
from secrets import mysecrets
import urequests
import time
        
def connect(index=2):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(mysecrets[index]['SSID'], mysecrets[index]['key'])
    while wlan.ifconfig()[0] == '0.0.0.0':
        print('.', end=' ')
        time.sleep(1)
    return wlan.ifconfig()