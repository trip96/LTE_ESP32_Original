# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
# import webrepl
# webrepl.start()

# boot.py -- run on boot-up
# can run arbitrary Python, but best to keep it minimal
#
import network
import time
import ntptime

# START DEBUG #


# END DEBUG #

ssid = 'MFT-Bridge'
password = '57708791'
mqtt_server = '192.168.168.139'
client_id = b'003'
topic_pub = b'Channel_LTE'

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)
# station.ifconfig(('192.168.168.16', '255.255.255.0', '192.168.168.1', '8.8.8.8'))

while station.isconnected() == False:
    print('Connecting...')
    time.sleep(1)
    pass

print('Connection successful')
print(station.ifconfig())
ntptime.settime()
time.sleep(2)