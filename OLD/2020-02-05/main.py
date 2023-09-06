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


#####################################
#####   Setup and Constants     #####
#####################################

# Custom SOCK for UART connection with 'FF' filter. 'FF' filter is in modbus package.
s = Modbus()

# Collect Garbage to keep memory clean
gc.collect()

# Global Variables for frequent polling to store. Only sending data every minute.
start_time = ''
temperature_string = ''

door_previous = ''
compressor_previous = ''
compressor_string = ''

# Frequent Poll Time
frequent_poll_interval = 3      # 3 seconds for quick polling actions like door status.
long_poll_interval = 60         # 60 Seconds for temperature polling.
send_interval = 600             # Time between pushes to MQTT broker.


# Watch dog timer to restart if system hangs for any reason. 120000 is 2 minutes. Value is in milliseconds (ms).
wdt = machine.WDT(timeout=(int(long_poll_interval * 1000) + 120000))


# MQTT Setup Values and Constants.

# mqtt_server = '138.197.128.162'           # Digital Ocean Test Service.
mqtt_server = 'soldier.cloudmqtt.com'       # The MQTT Server IP or DNS.
mqtt_user = 'zdufvknb'                      # Username for MQTT server.
mqtt_pass = 'eqBySOu8SHb-'                  # Password for MQTT server.
mqtt_port = 28099                           # Port for MQTT server.
# client_id = '007'                         # Client ID for the MQTT server.
# topic_sub = 't'                           # Topic to Subscribe to - Usually the RCU serial + '-C'
# topic_pub = 't'                           # Topic to publish messages to. Usually just the RCU serial.


# Colors for Terminal output readability.
class bcolors:
    HEADER = '\033[7m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


###########################################################
#####   Async Perpetual Functions for main program    #####
###########################################################

# Frequent polling used to capture state changes from Ascon Controller.
async def frequent_polling():
    global door_previous
    global compressor_previous
    global compressor_string
    while True:
        try:

            # Timing operation to account for dynamic Ascon response timings.
            tik = utime.ticks_ms()

            # MQTT check for Commands from Cloud via the Broker.
            client.check_msg()

            # Check for internet connectivity over the Simcom.
            check_ppp()

            # Dictionary returned from Ascon Module.
            frequent_results = ascon.frequent_polling()

            if frequent_results['door_status'] != door_previous:
                if frequent_results['door_status'] == 0:
                    send_event('c')
                    door_previous = frequent_results['door_status']
                else:
                    send_event('C')
                    door_previous = frequent_results['door_status']

            if frequent_results['compressor_status'] != compressor_previous:
                if frequent_results['compressor_status'] == 0:
                    compressor_string = compressor_string + decascii.time_delta(start_time=start_time,
                                                                                time=utime.time(), status=0)
                    compressor_previous = frequent_results['compressor_status']
                    print('Compressor String:' + compressor_string)
                else:
                    compressor_string = compressor_string + decascii.time_delta(start_time=start_time,
                                                                                    time=utime.time(), status=1)
                    compressor_previous = frequent_results['compressor_status']
                    print('Compressor String:' + compressor_string)

            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()
            time_delta = tok - tik
            # print('Time Delta : ' + str(time_delta))  # DEBUG - FOr showing time it takes to complete function.

            await uasyncio.sleep(frequent_poll_interval - (time_delta / 1000))  # In Milliseconds / 1000.

        except OSError as e:
            print(e)
            pass


# Long Polling Actions - Cabinet Temp, Evaporator Temp, Compressor Changes.
async def long_polling():
    global temperature_string
    global start_time

    while True:
        try:
            # Timing operation to account for dynamic Ascon response timings and Simcom Response / Timeouts.
            tik = utime.ticks_ms()

            # # Check if Simcom is in command mode and therefore dropped the data call.
            # try:
            #     if simcom.AT('', timeout=0)[0] == 'Success':
            #         print('Cellular Connection Lost.')
            #         close_restart()
            #     else:
            #         pass
            # except UnicodeError as e:
            #     print(e)
            #     pass

            # Time used to calculating additional time for compressor changes.
            start_time = utime.time()

            temps = ascon.get_temperatures()        # Variable (temps) must NOT be temperatures. So temps instead.

            # Sending results of Ascon controller through compression ASCII encoding module.
            temperature_string = temperature_string + decascii.d2a(temps[0]) + decascii.d2a(temps[1])

            # Check for known perpetual task bug.
            if len(temperature_string) > 40:
                print('Critical Error: Perpetual Tasks. Payload exceeds expected length.')
                close_restart()

            # Print the growing temperature string.
            print('Cabinet Temp:    ' + str(temps[0]))
            print('Evaporator Temp: ' + str(temps[1]))
            print('Temperature String: ' + temperature_string)

            # Feed the Watch dog to prevent reboot.
            wdt.feed()

            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()
            time_delta = tok - tik
            # print('Time Delta : ' + str(time_delta))  # DEBUG - FOr showing time it takes to complete function.

            # Feed the Watch dog to prevent reboot.
            wdt.feed()

            await uasyncio.sleep(long_poll_interval - (time_delta / 1000))  # In Milliseconds / 1000.

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

            # First capture the timestamp for the payload.
            ts = timestamp()

            # Wait for 600 seconds (10min).
            await uasyncio.sleep(send_interval)

            # Build the payload by adding everything together.
            payload = 'T' + ts + temperature_string + compressor_string     # 'T' is for Temperature.

            # Payload Info
            payload = str(payload)
            print(bcolors.OKGREEN + "PAYLOAD = " + payload + bcolors.ENDC)

            # Push payload through MQTT
            client.publish(rcu_serial, payload)

            # Collect garbage
            gc.collect()

            # Reset Payload Strings
            temperature_string = ''
            compressor_string = ''

        except:
            print('Critical Error in Building or Sending the Payload!')
            close_restart()
            pass


##################################
#####   Close and Restart    #####
##################################

def close_restart():
    print('Closing Connections.')
    ppp.active(False)
    time.sleep(1)
    simcom.simcom.read()
    print('Restarting in 10 seconds.')
    time.sleep(10)
    machine.reset()


#####################################
#####   PPP Connection Check    #####
#####################################

def check_ppp():
    if ppp.isconnected is False or str(ppp.ifconfig()[0]) == '0.0.0.0':
        print('Lost PPP connection.')
        close_restart()
    else:
        pass


######################################################
#####   Event and Alert Handling - MQTT Publish  #####
######################################################

def send_event(msg):
    client.publish(rcu_serial, msg + timestamp())
    print(bcolors.OKGREEN + 'Event Message: ' + msg + timestamp() + bcolors.ENDC)


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
    # Timestamp Reduction Encoding Schema Constants.
    ascii_offset = 33

    # Date variables.
    time_stamp = utime.localtime()
    year = time_stamp[0]-2000
    month = time_stamp[1]
    day = time_stamp[2]
    hour = time_stamp[3]
    minute = time_stamp[4]
    second = time_stamp[5]

    return chr(ascii_offset + int(year)) + chr(ascii_offset + int(month)) + chr(ascii_offset + int(day)) + \
              chr(ascii_offset + int(hour)) + chr(ascii_offset + int(minute)) + chr(ascii_offset + int(second))


#########################################
#####   First Procedures - Welcome  #####
#########################################

print('\r\n' + bcolors.HEADER + ' ##########     Welcome to Minus Forty IoT    ########## ' + bcolors.ENDC + '\r\n')

print('Boot and setup procedures will now start. Once complete perpetual tasks will resume.')
print('Watchdog has been engaged!')

#################################################################
#####   Initialization of Simcom and ON BOOT functions.     #####
#################################################################

print('\r\n' + bcolors.OKBLUE + ' - Setting up Simcom Modem - ' + bcolors.ENDC + '\r\n')

# SIMCOM.py Functions for prepping the cellular modem.
simcom.simcom.read()            # Flush Buffer.
simcom.simcom.write('+++')    # Cancel potential existing PPP mode to avoid unicode error.
simcom.power_off()              # Turn Off modem.
simcom.power_on()               # Turn ON modem.
simcom.init()                   # initialize the modem.
simcom.setup()                  # Setup the modem with APN etc.
simcom.simcom.read()            # Read the UART to make sure there are no straggling messages.
print('Waiting for Cellular Signal Check...')   # Wait 4 Seconds for CSQ to work correctly (Not return 99)
time.sleep(4)                   # Wait before asking CSQ.
simcom.csq()                    # Get Signal Quality.


######################################################################################
#####   Simcom PPP initialization for native micropython sockets over cellular.  #####
######################################################################################

print('\r\n' + bcolors.OKBLUE + ' - Setting up Cellular PPP Data Connection - ' + bcolors.ENDC + '\r\n')
print('Connecting to internet via PPP protocol. Wait 10 seconds.')

simcom.ppp_connect()
ppp = network.PPP(simcom.simcom)                # Attaching Simcom to the PPP network mod.
ppp.active(True)                                # Activate the ppp attachment.
ppp.connect()                                   # Connect the ppp attachment.
print('Waiting For IP address.')                # Wait before asking for IP.
time.sleep(5)                                   # Wait for Connection.
print(ppp.ifconfig())                           # Print the IP address to confirm connection is successful.

if ppp.isconnected() is True:
    print('Connected via PPP Data Layer.')
else:
    print('Connection Through PPP Failed.')
    close_restart()


###############################
#####   NTP Time Setup    #####
###############################

print('\r\n' + bcolors.OKBLUE + ' - Syncing RTC with NTP server - ' + bcolors.ENDC + '\r\n')
# Set RTC clock of ESP32 with time from NTP server. Must come after connection to internet.
ntp_sync_attempts = 0
while ntp_sync_attempts < 3:
    try:
        ntptime.settime()
        print(utime.localtime())
        break
    except:
        print('NTP clock Sync failed.')
        ntp_sync_attempts = ntp_sync_attempts + 1
        if ntp_sync_attempts >= 3:
            close_restart()

start_time = utime.time()       # Setting first global for calculating time deltas on Ascon Polling.


#############################################
#####   First Parameter Pull and Serial #####
#############################################

print('\r\n' + bcolors.OKBLUE + ' - Ascon RCU Setup - ' + bcolors.ENDC + '\r\n')

rcu_type = ascon.get_rcu_type()
rcu_serial = ascon.get_rcu_serial()
rcu_fw = ascon.get_rcu_fw()
rcu_params = ascon.get_rcu_param()

print('RCU Type: ' + rcu_type)
print('RCU Serial: ' + str(rcu_serial))
print('RCU Firmware: ' + str(rcu_fw))
print('RCU is Smart Lock 2? ' + str(ascon.is_smart_lock_2()))
print('RCU Params: ' + str(rcu_params))


#################################################################################
#####   MQTT Functions for connecting and dealing with lost connections.    #####
#################################################################################

print('\r\n' + bcolors.OKBLUE + ' - MQTT Connection Setup - ' + bcolors.ENDC + '\r\n')


def connect_and_subscribe():
    print('Trying to connect to MQTT')
    global rcu_serial, mqtt_server
    client = MQTTClient(rcu_serial, mqtt_server, ssl=True, user=mqtt_user, password=mqtt_pass, port=mqtt_port)
    client.set_callback(mqtt_command)
    client.connect()
    client.subscribe(rcu_serial + '-C')      # rcu_serial unique identifier and then C for 'command'.
    print('Connected to %s MQTT broker.' % mqtt_server)
    return client


def restart_and_reconnect():
    print('Failed to connect to MQTT broker.')
    close_restart()


# Initial MQTT connection and subscription.
try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()


##########################################
#####  Main Loop and ASYNC building  #####
##########################################

print('\r\n' + bcolors.OKGREEN + ' - BOOT COMPLETE AND OK! - ' + bcolors.ENDC + '\r\n')

print('\r\n' + bcolors.HEADER + ' ##########     Starting Perpetual Tasks    ########## ' + bcolors.ENDC + '\r\n')
# Asyncio Loops and Set up - Main loops for the entire program.

if __name__ == '__main__':
    # Get the event loop
    loop = uasyncio.get_event_loop()

    # Create the tasks
    loop.create_task(build_payload())
    loop.create_task(frequent_polling())
    loop.create_task(long_polling())

    # Run Built Tasks Loop Forever.
    loop.run_forever()
