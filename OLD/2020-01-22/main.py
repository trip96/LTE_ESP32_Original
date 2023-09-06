#################################################################################################
#####   Program for Ascon RCU wireless controlling. Written and Supported by cha Boi Kinno  #####
#################################################################################################

"""
This Program is intended for use by Minus Forty Technologies ltd. It is used to communicate with Ascon RCU's
Remotely via network technologies particularly WiFi and Cellular modems. This software / firmware contains modifications
to other open source modules such. This may cause unauthorized applications to function incorrectly. Minus Forty and
Kinno are not responsible for supporting this software outside of our Minus Forty Ecosystem.

main.py deals with large ideas and methods. main.py is where we set up the async loops and watch for mqtt messages
coming from the simcom chip. simcom.py is where we set up all cellular functions and use the built in MQTT functionality
that simcom provides. ascon.py uses our modified modbus library (located in /umodbus with the files funcitons.py,
const.py, and modbus.py) to interact with the ascon RCU controllers used in Minus Forty Refrigeration units.

main.py - Big picture - async loops, payload construction.
simcom.py - cellular connectivity, modem management, MQTT functionality.
ascon.py - functions for interacting with Ascon RCU's.
/umodbus - modified library for modbus interaction as used by ascon.py
param.py - Constant parameters used for querying registers in Ascon Controllers.
"""

######################
#####   Imports  #####
######################


import gc                               # Garbage collection for limited resource management.
from umodbus.modbus import Modbus       # Custom modification of modbus protocol.
import uasyncio                         # uasyncio - using for multiple methods simultaneously.
import simcom                           # Custom module written for Simcom 7000g chips.
import ascon                            # Custom module written for ASCON controller functions.
import machine                          # Micropython connection to ESP32 UART, Pins, GPIO etc.
import time                             # For sleeping and 'blocking' waiting.
import network                          # PPP modsocket library. Used for connecting to internet via Simcom.
import ntptime                          # Setting ESP32 RTC on boot with time From NTP server.
import utime                            # For Date and Time Stamping.
from umqtt.simple import MQTTClient     # MQTT Micropython Library
import decascii                         # Custom data compression for decimal numbers over MQTT.

# DEBUG LOGGING SECTION #

# END DEBUG SECTION #

#####################################
#####   Setup and Constants     #####
#####################################

# Custom SOCK for UART connection with 'FF' filter.
s = Modbus()

# Collect Garbage to keep memory clean
gc.collect()

# Global Variables for frequent polling to store. Only sending data every minute.
start_time = ''
cabinet_temp = ''
evap_temp = ''
temperature_string = ''

door_previous = ''
compressor_previous = ''
compressor_string = ''

# Frequent Poll Time
frequent_poll_interval = 3      # 3 seconds with an offset in order to account for controller delay in response. 2.69
long_poll_interval = 60             # 60 Second
send_interval = 600             # Time between pushes to MQTT broker.


# Watch dog timer to restart if system hangs for nay reason. 120000 is 2 minutes.
# wdt = machine.WDT(timeout=(int(send_interval * 1000) + 120000))

# MQTT Setup Values and Constants.

# mqtt_server = '138.197.128.162'
mqtt_server = 'soldier.cloudmqtt.com'
mqtt_user = 'zdufvknb'
mqtt_pass = 'eqBySOu8SHb-'
mqtt_port = 28099
client_id = '007'
topic_sub = 't'
topic_pub = 't'

# with open('ca.crt') as f:
#     ca_data = f.read()

# Encoding Schema Constants.
ascii_offset = 33


#################################################
#####   Async Functions for main program    #####
#################################################

# Frequent polling used to capture state changes from Ascon Controller.
async def frequent_polling():
    global door_previous
    global compressor_previous
    global compressor_string
    while True:
        try:

            tik = utime.ticks_ms()      # Timing operation to account for dynamic Ascon response timings.

            # MQTT check for Commands from Cloud via the Broker.
            client.check_msg()

            # Check Signal od simcom700g modem.
            simcom.csq()

            # Check for internet connectivity over the Simcom.
            check_ppp()

            # Dictionary returned from Ascon Module.
            frequent_results = ascon.frequent_polling()
            # print(str(frequent_results))

            if frequent_results['door_status'] != door_previous:
                if frequent_results['door_status'] == 0:
                    client.publish(rcu_serial, 'c' + timestamp())
                    print('c' + timestamp())
                    door_previous = frequent_results['door_status']
                else:
                    client.publish(rcu_serial, 'C' + timestamp())
                    print('C' + timestamp())
                    door_previous = frequent_results['door_status']

            if frequent_results['compressor_status'] != compressor_previous:
                if frequent_results['compressor_status'] == 0:
                    compressor_string = compressor_string + decascii.time_delta(start_time=start_time,
                                                                                time=utime.time(), status=0)
                    compressor_previous = frequent_results['compressor_status']
                    print('Compressor string is :' + compressor_string)
                else:
                    compressor_string = compressor_string + decascii.time_delta(start_time=start_time,
                                                                                    time=utime.time(), status=1)
                    compressor_previous = frequent_results['compressor_status']
                    print('Compressor string is :' + compressor_string)

            # # door_openings = frequent_results[0]
            # # door_open_time = frequent_results[1]
            # # compressor_on_time = frequent_results[2]
            # print(str(frequent_results))
            #
            # if frequent_results['door_status'] == 1:
            #
            # pr_1 = 40
            # pr_2 = 88
            #
            # payload = chr(pr_1) + chr(pr_2)
            # print(payload)
            # client.publish(rcu_serial, payload)

            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()
            time_delta = tok - tik
            print('Time Delta : ' + str(time_delta))

            await uasyncio.sleep(frequent_poll_interval - (time_delta / 1000))

        except OSError as e:
            print(e)
            pass


async def long_polling():
    global temperature_string
    global start_time

    while True:
        try:
            tik = utime.ticks_ms()      # Timing operation to account for dynamic Ascon response timings.

            start_time = utime.time()
            temps = ascon.get_temperatures()        # Variable (temps) must NOT be temperatures. So temps instead.
            temperature_string = temperature_string + decascii.d2a(temps[0]) + decascii.d2a(temps[1])

            payload = 'T' + temperature_string
            print('Temperature String: ' + temperature_string)


            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()
            time_delta = tok - tik
            print('Time Delta : ' + str(time_delta))

            await uasyncio.sleep(long_poll_interval - (time_delta / 1000))

        except OSError as e:
            print('Exception in Long Polling!')
            print(e)
            pass


# Building the payload for MQTT message. We also Check long poll information like Pr_1 and Pr_2.
async def build_payload():
    # global door_openings
    global temperature_string
    global compressor_string

    while True:
        try:

            # First add timestamp to payload.
            ts = timestamp()

            # Wait for 600 seconds (10min).
            await uasyncio.sleep(send_interval)

            # Build the payload by adding everything together.
            # Embarrassing way to add door_openings to the list....
            # First get temperatures because they are long poll time -  same as transfer time on info.

            # temperatures = ascon.get_temperatures()
            payload = 'T' + ts + temperature_string[:-1] + compressor_string

            # # Compressor on time Append to payload
            # if compressor_on_time > 0:
            #     payload.append((compressor_on_time/send_interval)*100)
            # else:
            #     payload.append(0)

            # Payload Info
            payload = str(payload)
            print("PAYLOAD = " + payload)

            # Publish to MQTT broker
            # payload = 'EYMDHMS,X1'
            # rcu_serial = '335466'

            client.publish(rcu_serial, payload)

            # Send to LTE module:

            # simcom.mqtt_pub(topic='XXXXXXXXX', msg=payload)

            # Print the time from RC clock updated via NTP function
            # print(str(utime.localtime()))

            # Collect garbage
            gc.collect()

            # # Reset Globals
            # door_openings = 0
            # door_open_time = 0
            # compressor_on_time = 0
            #
            # ascon.door_openings = 0
            # ascon.door_open_time = 0
            # ascon.compressor_on_time = 0
            temperature_string = ''
            compressor_string = ''

            # Feed the Watch dog to prevent reboot.
            # wdt.feed()

        except OSError:
            print('lost connection!')
            restart_and_reconnect()
            pass

#####################################
#####   PPP connection check    #####
#####################################


def check_ppp():
    if ppp.isconnected is False:
        print('Lost PPP connection. Restarting Device in 10 seconds.')
        time.sleep(10)
        machine.reset()
    else:
        print('PPP connection OK!')


######################################################
#####   Event and Alert Handling - MQTT Publish  #####
######################################################


def send_event(msg):
    client.publish(rcu_serial, msg)


def mqtt_command(topic, msg):
    print((topic, msg))
    print('Decoding values: ')
    print(msg)
    print(topic)
    print(msg[0])
    print(msg[1])


################################
#####   Date Processing    #####
################################


def timestamp():
    time_stamp = utime.localtime()
    year = time_stamp[0]-2000
    month = time_stamp[1]
    day = time_stamp[2]
    hour = time_stamp[3]
    minute = time_stamp[4]
    second = time_stamp[5]

    return chr(ascii_offset + int(year)) + chr(ascii_offset + int(month)) + chr(ascii_offset + int(day)) + \
              chr(ascii_offset + int(hour)) + chr(ascii_offset + int(minute)) + chr(ascii_offset + int(second))


#################################################################
#####   Initialization of Simcom and ON BOOT functions.     #####
#################################################################

# SIMCOM.py Functions for prepping the cellular modem #
simcom.power_off()
simcom.power_on()
simcom.init()           # initialize the modem
# simcom.restart()        # Restart Modem
simcom.setup()          # Setup the modem with APN etc.
simcom.simcom.read()    # Read the UART to make sure there are no straggling messages.


######################################################################################
#####   Simcom PPP initialization for native micropython sockets over cellular.  #####
######################################################################################

print('Connecting to internet via PPP protocol. Wait 10 seconds.')
simcom.simcom.write('AT+CGDATA="PPP",1\r\n')    # First data call fails for some reason TODO why?
time.sleep(5)
simcom.simcom.write('AT+CGDATA="PPP",1\r\n')    # Second data call for persisting connection.
time.sleep(2)
print(simcom.simcom.read())                     # Read the results of direct AT commands for PPP connection.
ppp = network.PPP(simcom.simcom)                # Attaching Simcom to the PPP network mod.
ppp.active(True)                                # Activate the ppp attachment.
ppp.connect()                                   # Connect the ppp attachment.
time.sleep(5)
print(ppp.ifconfig())                           # Print the IP address to confirm connection is successful.

if ppp.isconnected() is True:
    print('Connected!')
else:
    print('Connection failed. Restarting in 15 seconds')
    time.sleep(15)
    machine.reset()

###############################
#####   NTP Time Setup    #####
###############################


# Set RTC clock of ESP32 with time from NTP server. Must come after connection to internet.
try:
    print('Syncing NTP time with RTC clock of ESP32')
    ntptime.settime()
    print('NTP time Synced!')
    print(utime.localtime())

except:
    print('NTP clock Sync failed. Restarting in 15 seconds')
    ppp.active(False)
    time.sleep(15)
    machine.reset()

start_time = utime.time()

#############################################
#####   First Parameter Pull and Serial #####
#############################################


print('Detecting RCU...')

rcu_type = ascon.get_rcu_type()
rcu_serial = ascon.get_rcu_serial()
rcu_fw = ascon.get_rcu_fw()
rcu_params = ascon.param_pull()

print('RCU Type: ' + rcu_type)
print('RCU Serial: ' + str(rcu_serial))
print('RCU Firmware: ' + str(rcu_fw))
print('RCU Params: ' + str(rcu_params))
print('RCU detection complete.')


#################################################################################
#####   MQTT Functions for connecting and dealing with lost connections.    #####
#################################################################################


def connect_and_subscribe():
    print('Trying to connect to MQTT')
    global rcu_serial, mqtt_server, rcu_serial
    client = MQTTClient(rcu_serial, mqtt_server, ssl=True, user=mqtt_user, password=mqtt_pass, port=mqtt_port)
    client.set_callback(mqtt_command)
    client.connect()
    client.subscribe(rcu_serial + 'C')      # rcu_serial unique identifier and then C for 'command'.
    print('Connected to %s MQTT broker.' % mqtt_server)
    return client


def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Restarting in 15 sec...')
    ppp.active(False)
    time.sleep(15)
    machine.reset()


# Initial MQTT connection and subscription.
try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()


##########################################
#####  Main Loop and ASYNC building  #####
##########################################

# Asyncio Loops and Set up - Main loops for the entire program.

if __name__ == '__main__':
    # Get the event loop
    loop = uasyncio.get_event_loop()

    # Create the tasks
    loop.create_task(frequent_polling())
    loop.create_task(long_polling())
    loop.create_task(build_payload())
    loop.run_forever()
