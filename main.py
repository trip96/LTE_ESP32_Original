#################################################################################################
#####   Program for Ascon RCU wireless controlling. Written and Supported by cha Boi Kinno  #####
#################################################################################################

"""
This Program is intended for use by Minus Forty Technologies ltd. It is used to communicate with Ascon RCU's
Remotely via network technologies particularly WiFi and Cellular modems. This software / firmware contains modifications
to known standards. This may cause unauthorized applications to function incorrectly. Minus Forty is not responsible
for supporting this software outside of our Minus Forty Ecosystem.

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

import machine                          # Micropython connection to ESP32 UART, Pins, GPIO etc.

# Watch dog timer to restart if system hangs for any reason. 120000 is 2 minutes. Value is in milliseconds (ms).
# Must start this as soon as possible in case of import failures. Must come after import machine as machine import
# gives access to watchdog.

wdt = machine.WDT(timeout=(int(60 * 1000) + 120000))    # Hard code the 'Long_poll_interval' (default 60 seconds).

import gc                               # Garbage collection for limited resource management.
import time                             # For sleeping and 'blocking' waiting.
from umodbus.modbus import Modbus       # Custom modification of modbus protocol.
import uasyncio                         # uasyncio - using for multiple methods simultaneously.
import simcom                           # Custom module written for Simcom 7000g chips.
import network                          # PPP modsocket library. Used for connecting to internet via Simcom.
import ntptime                          # Setting ESP32 RTC on boot with time From NTP server.
import utime                            # For Date and Time Stamping.
from umqtt.simple import MQTTClient     # MQTT Micropython Library
import decascii                         # Custom data compression for decimal numbers over MQTT.
import ascon                            # Custom module written for ASCON controller functions. RCU type query here.
import ujson                            # For sending and receiving json payloads.


#####################################
#####   Setup and Constants     #####
#####################################

# Custom SOCK for UART connection with 'FF' filter. 'FF' filter located in the modbus package. Ascon UART bus.
s = Modbus()

# Collect Garbage to keep memory clean.
gc.collect()

# Event Locking to make sure TEMP payload is exactly 40 Chars long (10min).
event = uasyncio.Event()

# Global Variables for frequent polling to store. Only sending data every minute.
temperature_string = ''     # String to hold the temperature while we wait for 10min push.

door_previous = 0         # Set as off as most common value. Do not need to send this on boot if not needed.
defrost_previous = 0      # Set as off as most common value. Do not need to send this on boot if not needed.

# Alerts All set to no as that's most common.
high_temp_alert = 'no'
low_temp_alert = 'no'
malfunctioning_alert = 'no'
door_open_alert = 'no'

# Frequent Poll Time
frequent_poll_interval = 3                  # 3 seconds for quick polling actions like door status.
long_poll_interval = 60                     # 60 Seconds for temperature polling. Hard code to watchdog is changed.
send_interval = 600                         # Time between pushes to MQTT broker. In seconds. 600 sec is 10 min


# MQTT Setup Values and Constants.
# mqtt_server = '138.197.128.162'           # Digital Ocean Test Service.
mqtt_server = 'soldier.cloudmqtt.com'       # The MQTT Server IP or DNS.
mqtt_user = 'zdufvknb'                      # Username for MQTT server.
mqtt_pass = 'eqBySOu8SHb-'                  # Password for MQTT server.
mqtt_port = 28099                           # Port for MQTT server.
# client_id = '007'                         # Client ID for the MQTT server.
# topic_sub = 't'                           # Topic to Subscribe to - Usually the RCU serial + '-C'
# topic_pub = 't'                           # Topic to publish messages to. Usually just the RCU serial.


# Colors for Terminal output readability. Will most likely never need adjusting.
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

# Frequent polling used to capture state changes from Ascon Controller. Door Status, Alarms, etc.
async def frequent_polling(lock):
    # Globals for holding previous values and alerts from the polling.
    global door_previous
    global defrost_previous
    global high_temp_alert
    global low_temp_alert
    global malfunctioning_alert
    global door_open_alert

    while True:     # Keep Running Forever.
        try:        # Usually pass on small errors to keep program running.

            # Timing operation to account for dynamic Ascon response timings. Get the payload to 1min interval.
            tik = utime.ticks_ms()      # Set the start time for this task.

            # Dictionary returned from Ascon Module. Ascon Module does the polling.
            await lock.acquire()    # Lock the UART - Preventing Collisions.
            frequent_results = ascon.frequent_polling()     # Get the dictionary.
            utime.sleep_ms(100)     # Slow Ascon - Preventing Collisions.
            lock.release()          # Unlock the UART.

            # print(frequent_results)     # For debugging the frequent polling.

            # Process the Polling object.

            # Door Status Processing
            if frequent_results['door_status'] != door_previous:    # Make sure status has changed.
                if frequent_results['door_status'] == 0:            # Is it open or closed?
                    send_event('c')     # Door is closed.
                    door_previous = frequent_results['door_status']
                elif frequent_results['door_status'] == 1:
                    send_event('C')     # Door is Open.
                    door_previous = frequent_results['door_status']
                else:
                    print('Door Error.')
                    print(frequent_results['door_status'])

            # Defrost Status Processing
            # if frequent_results['defrost_status'] != defrost_previous:      # Make sure status has changed.
            #     if frequent_results['defrost_status'] == 0:                 # Is it on or off?
            #         send_event('a')     # Defrost is OFF.
            #         defrost_previous = frequent_results['defrost_status']
            #     else:
            #         send_event('A')     # Defrost is ACTIVE.
            #         defrost_previous = frequent_results['defrost_status']

            # High Temp Alarm
            if high_temp_alert != frequent_results['high_temp_alert']:      # Make sure status has changed.
                if frequent_results['high_temp_alert'] == 'yes':
                    print('high_temp ALERT IS ACTIVE!')
                    high_temp_alert = frequent_results['high_temp_alert']
                if frequent_results['high_temp_alert'] == 'no':
                    print('high_temp ALERT IS CLEARED!')
                    high_temp_alert = frequent_results['high_temp_alert']

            # Low Temp Alarm
            if low_temp_alert != frequent_results['low_temp_alert']:        # Make sure status has changed.
                if frequent_results['low_temp_alert'] == 'yes':
                    print('low_temp ALERT IS ACTIVE!')
                    high_temp_alert = frequent_results['high_temp_alert']
                if frequent_results['low_temp_alert'] == 'no':
                    print('low_temp ALERT IS CLEARED!')
                    high_temp_alert = frequent_results['low_temp_alert']

            # Door Open Alarm
            if door_open_alert != frequent_results['door_open_alert']:      # Make sure status has changed.
                if frequent_results['door_open_alert'] == 'yes':
                    print('door_open ALERT IS ACTIVE!')
                    high_temp_alert = frequent_results['high_temp_alert']
                if frequent_results['door_open_alert'] == 'no':
                    print('door_open IS CLEARED!')
                    high_temp_alert = frequent_results['door_open_alert']

            # Malfunctioning Alarm
            if malfunctioning_alert != frequent_results['malfunctioning_alert']:        # Make sure status has changed.
                if frequent_results['malfunctioning_alert'] == 'yes':
                    print('malfunctioning_alert ALERT IS ACTIVE!')
                    high_temp_alert = frequent_results['malfunctioning_alert']
                if frequent_results['malfunctioning_alert'] == 'no':
                    print('malfunctioning_alert IS CLEARED!')
                    high_temp_alert = frequent_results['malfunctioning_alert']

            #  MQTT check for Commands from Cloud via the Broker.

            await lock.acquire()    # Lock to prevent collisions.
            client.check_msg()      # Must be at end of script as causes problems with polling of RCU. NoneType #TODO
            lock.release()          # Release the lock.

            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()      # Set the time the task finished
            time_delta = tok - tik      # Calculate how long the task took. Subtract from ideal time to get real wait.
            # print('Frequent - Delta : ' + str(time_delta))  # DEBUG.

            await uasyncio.sleep(frequent_poll_interval - (time_delta / 1000))  # In milliseconds / 1000.

        except Exception as e:
            print('Error in Main program frequent polling async.')
            print(e)
            close_restart()


# Long Polling Actions - Cabinet Temp, Evaporator Temp, Compressor Changes.
async def long_polling(lock):
    global temperature_string

    while True:
        try:
            # Timing operation to account for dynamic Ascon response timings and Simcom Response / Timeouts.
            tik = utime.ticks_ms()      # Set the start time of this task.

            await lock.acquire()
            temps = ascon.get_temperatures()        # Variable (temps) must NOT be temperatures. So temps instead.
            utime.sleep_ms(100)                     # Needed because ASCON RCU slow.
            lock.release()

            # Sending results of Ascon controller through compression ASCII encoding module.
            temperature_string = temperature_string + decascii.d2a(temps[0]) + decascii.d2a(temps[1])

            # Make sure the Payload is exactly 40 Chars long.
            if len(temperature_string) == 40:
                event.set()     # Allow the Build payload to proceed. It is waiting for this call.

            # Second part of time function for accounting for Ascon dynamic response timings.
            tok = utime.ticks_ms()  # Set the time the task finished
            time_delta = tok - tik  # Calculate how long the task took. Subtract from ideal time to get real wait.
            # print('Long - Delta : ' + str(time_delta))  # DEBUG.

            wdt.feed()      # Feed the Watch dog to prevent reboot.

            await uasyncio.sleep(long_poll_interval - (time_delta / 1000))  # In Milliseconds / 1000.

        except Exception as e:
            # print('Exception in Long Polling!')
            # print(e)
            pass


# Building the payload for MQTT message. We also Check long poll information like Pr_1 and Pr_2.
async def build_payload():
    # global door_openings
    global temperature_string
    time_delta = 0       # Initial Time delta needed because this task waits then executes.

    while True:
        try:
            # First capture the timestamp for the payload.
            # ts = timestamp()

            # Wait for 600 seconds (10min).
            await uasyncio.sleep(send_interval - 30 - (time_delta / 1000))       # -30 for no more than 40 chars. # TODO

            await event.wait()      # Waiting for Long Pool to have 40 chars Temps string.

            tik = utime.ticks_ms()  # Set the start time of this task.

            # Build the payload by adding everything together.
            # payload = 'T' + ts + temperature_string     # 'T' is for Temperature.
            payload = 'T' + temperature_string     # 'T' is for Temperature.

            event.clear()       # Clear event for Long Poll and Build Payload.

            # Push payload through MQTT
            client.publish(rcu_serial, payload, qos=1)

            # Payload Info - Printed after the MQTT message was published.
            payload = str(payload)
            print(utime.localtime())
            print(bcolors.OKGREEN + "PAYLOAD = " + payload + bcolors.ENDC)

            # Collect garbage
            gc.collect()

            # Reset Payload String
            temperature_string = ''

            tok = utime.ticks_ms()  # Set the time the task finished
            time_delta = tok - tik  # Calculate how long the task took. Subtract from ideal time to get real wait.
            # print('Build - Time Delta is: ' + str(time_delta))

        except Exception as e:
            print('Critical Error in Building or Sending the Payload!')
            print(e)
            close_restart()
            pass


##################################
#####   Close and Restart    #####
##################################

def close_restart():
    print('Closing Connections.')
    ppp.active(False)
    time.sleep(1)
    simcom.simcom.write('+++')  # Cancel potential existing PPP mode to avoid unicode error.
    time.sleep(1)
    simcom.simcom.read()    # Clear Simcom Serial Buffer
    time.sleep(1)
    simcom.deinit()         # Deinit the simcom UART
    ascon.deinit()          # Deinit the Ascon UART
    print('Restarting in 10 seconds.')
    time.sleep(10)
    machine.reset()         # Reset the Machine.


######################################################
#####   Event and Alert Handling - MQTT Publish  #####
######################################################

def send_event(msg):
    # client.publish(rcu_serial, msg + timestamp())
    client.publish(rcu_serial, msg)
    # print(bcolors.OKGREEN + 'Event Message: ' + msg + timestamp() + bcolors.ENDC)
    print(bcolors.OKGREEN + 'Event Message: ' + msg + bcolors.ENDC)


#############################################################
#####   Incoming Commands - MQTT Command Processing     #####
#############################################################

def mqtt_command(topic, msg):
    # globals for publishing
    global rcu_serial

    try:
        print((topic, msg))
        # print('Decoding values: ')
        decoded = msg.decode("utf-8").split(',')
        # print("Command is: " + decoded[0])
        # print("Value 1 is: " + decoded[1])
        # utime.sleep_ms(500)     # Needed because ASCON RCU slow.

        # Querying a register on the RCU - Returns the Value from the register.
        if decoded[0] == 'r':
            reply = ascon.query_rcu([str(decoded[1])])
            client.publish(rcu_serial, str(reply))

        # Writting to a register on the RCU.
        elif decoded[0] == 'w':
            reply = 'e: ' + str(ascon.write_register(register_address=decoded[1], value=decoded[2]))
            client.publish(rcu_serial, str(reply))

        # Diagnostic and full parameters from RCU.
        elif decoded[0] == 'p':
            rcu_type = ascon.get_rcu_type()
            rcu_serial = ascon.get_rcu_serial()
            rcu_fw = ascon.get_rcu_fw()
            rcu_params = ascon.get_rcu_param()

            rcu_info = {
                "RCU Type": rcu_type,
                "RCU Serial": rcu_serial,
                "RCU Firmware": rcu_fw,
                "RCU Parameters": rcu_params,
                      }

            ujson.dumps(rcu_info)

            client.publish(rcu_serial, str(rcu_info))

        elif decoded[0] == 'ip':
            client.publish(rcu_serial, str(ppp.ifconfig()))

        # Soft restart
        elif decoded[0] == 'restart':
            close_restart()

        else:
            # await lock.acquire()
            client.publish(rcu_serial, 'Command Not Recognized!')

        utime.sleep_ms(500)     # Needed because ASCON RCU slow.

    except Exception as e:
        print('Problem Writting Command!')
        print(e)
        client.publish(rcu_serial, 'Error processing the command!')
        pass


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
print('Imports and functions have successfully been loaded.')
print('Watchdog has been engaged!')


#################################################################
#####   Initialization of Simcom and ON BOOT functions.     #####
#################################################################

print('\r\n' + bcolors.OKBLUE + ' - Setting up Simcom Modem - ' + bcolors.ENDC + '\r\n')

# SIMCOM.py Functions for prepping the cellular modem.
simcom.simcom.read()            # Flush Buffer.
simcom.simcom.write('+++')      # Cancel potential existing PPP mode to avoid unicode error.
simcom.power_off()              # Turn Off modem.
simcom.power_on()               # Turn ON modem.
simcom.simcom.read()            # Flush Buffer.
simcom.setup()                  # Setup the modem with APN etc.
simcom.simcom.read()            # Read the UART to make sure there are no straggling messages.
print('Waiting for Cellular Signal Check... 4 Seconds.')   # Wait 4 Seconds for CSQ to work correctly (Not return 99)
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
print('Waiting For IP address. 6 Seconds.')     # Wait before asking for IP.
time.sleep(6)                                   # Wait for Connection. 5 sec can work trying 6.
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
    except Exception as e:
        print('NTP clock Sync failed. Waiting 3 seconds. Then trying again.')
        print(e)
        ntp_sync_attempts = ntp_sync_attempts + 1
        time.sleep(3)
        if ntp_sync_attempts >= 3:
            print('NTP clock failed to sync 3 times!')
            close_restart()


#############################################
#####   First Parameter Pull and Serial #####
#############################################

print('\r\n' + bcolors.OKBLUE + ' - Ascon RCU Setup - ' + bcolors.ENDC + '\r\n')
rcu_type = ascon.get_rcu_type()

# if rcu_type == 'RCU Not Recognized':
# #     client.publish(gps_coordinates, 'RCU ERROR', qos=1)             # TODO Mac address and GPS cordinates.
rcu_serial = ascon.get_rcu_serial()
rcu_fw = ascon.get_rcu_fw()
rcu_params = ascon.get_rcu_param()

print('Getting RCU information. This will take 5 seconds')
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
    print('Can Not Connect to MQTT Host')
    print(e)
    restart_and_reconnect()


##########################################
#####  Main Loop and ASYNC building  #####
##########################################

print('\r\n' + bcolors.OKGREEN + ' - BOOT COMPLETE AND OK! - ' + bcolors.ENDC + '\r\n')

print('\r\n' + bcolors.HEADER + ' ##########     Starting Perpetual Tasks    ########## ' + bcolors.ENDC + '\r\n')
# Asyncio Loops and Set up - Main loops for the entire program.

if __name__ == '__main__':
    lock = uasyncio.Lock()
    # Get the event loop
    loop = uasyncio.get_event_loop()

    # Create the tasks
    loop.create_task(build_payload())
    loop.create_task(frequent_polling(lock))
    loop.create_task(long_polling(lock))

    # Run Built Tasks Loop Forever.
    loop.run_forever()
