#########################################################################################
##### Simcom 7000g methods and AT scripts for use with the Minus Forty IoT project  #####
#########################################################################################

""" This is a custom module written by Jordan MacKinnon and intended for use with ESP32 and Simcom 7000g. Using a
modified TTGO T-Call module. This is based on other works regarding simcom modules and is not intended to work
outside the Minus Forty Ecosystem. Any support outside of this ecosystem  will not be provided."""

###################################################
##### IMPORTS AND REQUIREMENTS FOR SIMCOM.PY  #####
###################################################

from machine import UART        # ESP32 UART interface for connecting to SIM7000g.
from machine import Pin         # ESP32 UART PIN definitions.
import time
import gc                       # Garbage Collection for keeping memory clean.


# Collect garbage after imports to keep things clean.
gc.collect()

####################################################################
##### SETUP AND CUSTOMIZATION FOR SIMCOM APN AND MQTT SETTINGS #####
####################################################################


# Cellular Network Setup

apn = 'm2minternet.apn'                 # Cellular network APN


# Power Pin and Control for Simcom 7000.
# Cell PIN power Machine pins. These control the power of the simcom chip.
cell_power = Pin(4, Pin.OUT)    # PIN 4 on ESP32 controls power of Simcom.
cell_power.on()                 # Make sure PIN 4 is HIGH.

# Setting up UART to SIMCOM 7000 chip.

# Initialization at start.
simcom = UART(1, 9600)  # init with given baudrate
simcom.init(baudrate=9600, bits=8, parity=None, stop=1, rx=26, tx=27)  # init with given parameters check rx and tx.


def init():
    simcom = UART(1, 9600)  # init with given baudrate
    simcom.init(baudrate=9600, bits=8, parity=None, stop=1, rx=26, tx=27)  # init with given parameters check rx and tx.


def deinit():
    simcom.deinit()



###########################################################################
##### MAIN FUNCTIONS RELATED TO SIMCOM MODEM VIA UART AND AT COMMANDS #####
###########################################################################

# AT commands for SIMCOM 7000 in relation to MFT - Basic functions.

# CMD line break for AT function -  Need this for modem to accept commands. Equiv to 'enter' or 'submit' on a form.
CMD_LINEBREAK = b'\r\n'


# Write data through UART to Simcom
def send(data):
    simcom.write(data)      # Do the write.


# Encode the Commands and send.
def send_cmd(cmd):
    send(cmd.encode('utf-8') + CMD_LINEBREAK)       # Package the command and encode in UTF-8


# Watching for data from the Simcom modem over UART. This is  the main function for handling data in and out of Simcom.
def watch(timeout=10, success=None, failure=None, echo_cmd=None):
    t_start = time.time()  # For timing how long the reply takes.
    reply = list()
    while True:
        try:
            if simcom.any():  # If there is data on UART 1 - connected to Simcom.
                line = simcom.readline()    # Read the line of data from UART.
                echo = False        # Start with the echo set to False
                if echo_cmd:
                    echo = line.decode('utf-8').strip().endswith(echo_cmd)  # Decode and strip the reply
                if line != CMD_LINEBREAK and not echo:              # Process the reply.
                    line = line.decode('utf-8').strip()
                    reply.append('\t' + line)
                    if success and line.startswith(success):  # handle the reply according to 'if' situations.
                        return "Success", reply, time.time() - t_start
                    if failure and line.startswith(failure):
                        return "Error", reply, time.time() - t_start
            if (time.time() - t_start) > timeout:
                return "Timeout", reply, time.time() - t_start
            time.sleep_ms(20)
        except:
            pass    # Broad pass to keep program running. Often times it is OK with simcom.


# AT command function for communicating with Simcom
def AT(cmd="", timeout=10, success="OK", failure="+CME ERROR"):
    cmd = 'AT' + cmd
    # print("----------- ", cmd, " -----------")
    send_cmd(cmd)
    reply = watch(timeout=timeout, success=success, failure=failure, echo_cmd=cmd)
    # print("{0} ({1:.2f}secs):".format(reply[0], reply[2]))
    # print(*reply[1], sep='\n')
    # print('')
    return reply


# Power on function for Simcom Modem
def power_on():
    print("Powering ON Modem.")
    simcom.read()
    AT('', timeout=0)
    cell_power.on()
    print('Waiting 7 seconds for modem boot procedures.')
    time.sleep(7)
    simcom.read()
    AT('', timeout=10)
    AT('+CPIN?')
    online = AT('+GSN')
    print(online[0] + '')
    if online[0] is 'Error':
        print('Modem did not Turn On.')
        raise OSError('Modem Did not respond to GSN command on Power up!')
    print('Modem is now ON.')


# Power off function for Simcom modem.
def power_off():
    print("Powering Off Modem.")
    cell_power.off()
    time.sleep(1)
    cell_power.off()
    time.sleep(1)
    print('Cell Modem is now OFF.')


# Restart the Simcom Modem.
def restart():
    print("Restarting Modem\n")
    simcom.read()
    AT('+CIPSHUT', success='SHUT OK')
    AT('+CFUN=1,1', timeout=30, success="SMS Ready")
    simcom.read()


# Full setup process for Simcom. required on bugs or initial setups.
def setup():
    print("Running Modem Setup Scripts")
    simcom.read()
    deinit()
    time.sleep_ms(300)
    init()
    time.sleep_ms(300)
    simcom.read()
    AT('', timeout=1)
    AT('', timeout=1)
    AT('+IPR=9600')
    # AT('+CGNSPWR=1')                        # GPS Power ON
    AT('+GSN')
    AT('+CPIN?')
    AT('+CFUN=1')
    AT('+CMNB=1')
    AT('+CSTT="' + apn + '","",""')
    AT('+CGDCONT=1,"IP","' + apn + '"')
    AT('S7=10')
    if AT('+CCID')[0] == 'Error':
        raise OSError('Modem Setup Procedure did not respond to CCID command')
    else:
        print('Modem Setup Scripts are Successful')


def ppp_connect():
    AT('+CGDATA="PPP",1', success='NO CARRIER', timeout=5)             # TODO First call often fails.... Why?
    if AT('+CGDATA="PPP",1', timeout=0)[0] == 'Timeout':               # TODO Second Call Connects Immediately. Why?
        print('PPP Call Established.')
    else:
        print('PPP Call Failed.')


# Signal Quality Check
def csq():
    try:
        signal = AT('+CSQ')
        value = signal[1][0].split(': ')[1].split(',')[0]
        percentage = round((int(value) / 28) * 100)
        if int(value) < 10:
            print('Signal Quality is - Poor - ' + str(percentage) + '%')
        elif int(value) < 15:
            print('Signal Quality is - OK - ' + str(percentage) + '%')
        elif int(value) < 20:
            print('Signal Quality is - Good - ' + str(percentage) + '%')
        else:
            print('Signal Quality is - Excellent - ' + str(percentage) + '%')
    except Exception as e:
        print('Problem Reading CSQ quality!')
        print(e)
        return 'Error with CSQ!'


# Ping NTP for global time
def ntp_time():
    print("\nNTP\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(apn))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+CNTP="pool.ntp.org",0,1,1')
    date_time = AT('+CNTP', timeout=3, success="+CNTP")[1][1].split('"')[1]
    AT('+SAPBR=0,1')
    return date_time
#
#
# def get_gps():
#     AT('+CGNSPWR=1')
#     gps = AT('+CGNSINF')
#     return gps
