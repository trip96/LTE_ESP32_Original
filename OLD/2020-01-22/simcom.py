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
import os                       # Micropython OS library for interacting with OS.
import time                     # Time module for sleeping.
import gc                       # Garbage Collection for keeping memory clean.


# Collect garbage after imports to keep things clean.
gc.collect()

####################################################################
##### SETUP AND CUSTOMIZATION FOR SIMCOM APN AND MQTT SETTINGS #####
####################################################################


# Cellular Network Setup

apn = 'm2minternet.apn'                 # Cellular network APN

# # MQTT Settings   -   Settings For USING MQTT FUNCTION OF SIMCOM INSTEAD OF uPYTHON.
#
# rcu_serial = 'init'
#
# mqtt_server = '138.197.128.162'
# mqtt_port = '1883'
# client_id = '003'
# topic_pub = rcu_serial
# topic_sub = rcu_serial
# mqtt_user = 'LTE-Test'
# mqtt_pass = 'spiderman'
#
# mqtt_msg = ''
# mqtt_new = False

# # TLS Certificates Configuration  - For Server validation of clients.
#
# certs_folder = 'certs'
# ca_name = 'mqtt-ca.crt'
# cert_name = "mqt.crt"
# key_name = "mqtt.key"

# Setting up UART to SIMCOM 7000 chip.

# Initialization at start.
simcom = UART(1, 9600)  # init with given baudrate
simcom.init(baudrate=9600, bits=8, parity=None, stop=1, rx=26, tx=27)  # init with given parameters check rx and tx.


def init():
    simcom = UART(1, 9600)  # init with given baudrate
    simcom.init(baudrate=9600, bits=8, parity=None, stop=1, rx=26, tx=27)  # init with given parameters check rx and tx.


def deinit():
    simcom.deinit()


# Cell PIN power Machine pins. These control the power of the simcom chip.
cell_power = Pin(4, Pin.OUT)    # PIN 4 on ESP32 controls power of Simcom.
cell_power.on()                 # Make sure PIN 4 is HIGH.

###########################################################################
##### MAIN FUNCTIONS RELATED TO SIMCOM MODEM VIA UART AND AT COMMANDS #####
###########################################################################

# AT commands for SIMCOM 7000 in relation to MFT - Basic functions.

# CMD line break for AT function -  Need this for modem to accept commands. Equiv to 'enter' or 'submit' on a form.
CMD_LINEBREAK = b'\r\n'


# Write data through UART to Simcom
def send(data):
    simcom.write(data)


# Encode the Commands and send.
def send_cmd(cmd):
    send(cmd.encode('utf-8') + CMD_LINEBREAK)


# Watching for data from the Simcom modem over UART. This is  the main function for handling data in and out of Simcom.
def watch(timeout=10, success=None, failure=None, echo_cmd=None):
    t_start = time.time()  # For timing how long the reply takes.
    reply = list()
    while True:
        if simcom.any():  # If there is data on UART 1 - connected to Simcom.
            line = simcom.readline()
            echo = False
            if echo_cmd:
                echo = line.decode('utf-8').strip().endswith(echo_cmd)  # Decode and strip the reply
            if line != CMD_LINEBREAK and not echo:
                line = line.decode('utf-8').strip()
                reply.append('\t' + line)
                if success and line.startswith(success):  # handle the reply according to 'if' situations.
                    return "Success", reply, time.time() - t_start
                if failure and line.startswith(failure):
                    return "Error", reply, time.time() - t_start
                #############################################################################################
                ## MQTT RELATED FUNCTIONS ##
                # if line.startswith('+SMSUB: '):  # For replies that COME FROM MQTT via Simcom. Buggy ATM
                #     r = line.split(': ')
                #     r = r[1].split(',')
                #     # print('MQTT MSG RECEIVED! - ' + str(r))
                #     # return ('MQTT', r)
                #     mqtt_callback(r)  # Function that handles the message from the MQTT running on Simcom.
                #     # break  # Break out of this watch function. May introduce bugs.
                ##############################################################################################
        if (time.time() - t_start) > timeout:
            return "Timeout", reply, time.time() - t_start
        time.sleep_ms(20)


# AT command function for communicating with Simcom
def AT(cmd="", timeout=10, success="OK", failure="+CME ERROR"):
    cmd = 'AT' + cmd
    print("----------- ", cmd, " -----------")
    send_cmd(cmd)
    reply = watch(timeout=timeout, success=success, failure=failure, echo_cmd=cmd)
    print("{0} ({1:.2f}secs):".format(reply[0], reply[2]))
    print(*reply[1], sep='\n')
    print('')
    return reply


# Power on function for Simcom Modem
def power_on():
    print("++++++++++++++++++++ Powering ON Modem +++++++++++++++++++++\n")
    AT('', timeout=0)
    print('Powering UP Cell Modem.')
    cell_power.on()
    print('Modem Power Switch Activated to ON.')
    print('Waiting 7 seconds for modem boot procedures.')
    time.sleep(7)
    simcom.read()
    AT('', timeout=10)
    AT('+CPIN?')
    online = AT('+GSN')
    print(online[0])
    if online[0] is 'Error':
        print('Modem did not Turn On.')
    print('Power on cycle complete.')


# Power off function for Simcom modem.
def power_off():
    print("++++++++++++++++++++ Powering Off Modem +++++++++++++++++++++\n")
    AT('', timeout=1)
    AT('', timeout=1)
    print('Powering Down Cell Modem')
    cell_power.off()
    AT('+CPOWD=1', timeout=30, success='NORMAL POWER DOWN')
    time.sleep(1)
    print('Cell Modem is now OFF')


# Restart the Simcom Modem.
def restart():
    print("++++++++++++++++++++ Restarting Modem +++++++++++++++++++++\n")
    simcom.read()
    AT('+CIPSHUT', success='SHUT OK')
    AT('+CFUN=1,1', timeout=30, success="SMS Ready")
    simcom.read()


# Full setup process for Simcom. required on bugs or initial setups.
def setup():
    print("++++++++++++++++++++ Setting Up Modem +++++++++++++++++++++\n")
    deinit()
    init()
    AT('', timeout=1)
    AT('', timeout=1)
    AT('+IPR=9600')
    AT('+GSN')
    AT('+CPIN?')
    AT('+CSQ')
    AT('+CMNB=1')
    simcom.read()
    AT('', timeout=1)
    AT('', timeout=1)
    AT('+CSTT="' + apn + '","",""')
    AT('+CGDCONT=1,"IP","' + apn + '"')

    ## Legacy methods   ##
    # AT('+CIPSHUT', success='SHUT OK')
    # print('OK')
    # send_cmd('ATD*99***1#\r\n')
    # time.sleep(5)
    # print('OK')
    # simcom.read()
    # print('OK')
    # AT('+CIICR')
    # AT('+CGATT=1')
    # AT('+CREG=1')
    # AT('+CIPSHUT', success='SHUT OK')
    # AT('+CIPMUX=0')
    # AT('+CIPRXGET=0')
    # AT('+CIPMODE=1')


# Signal Quality Check
def csq():
    print("++++++++++++++++++++ Signal Quality +++++++++++++++++++++\n")
    signal = AT('+CSQ')
    value = signal[1][0].split(': ')[1].split(',')[0]
    if int(value) < 10:
        print('Poor')
    elif int(value) < 15:
        print('OK')
    elif int(value) < 20:
        print('Good')
    else:
        print('Excellent')
    print(value)


# Ping NTP for global time
def ntp_time():
    print("++++++++++++++++++++ NTP +++++++++++++++++++++\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(apn))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+CNTP="pool.ntp.org",0,1,1')
    date_time = AT('+CNTP', timeout=3, success="+CNTP")[1][1].split('"')[1]
    AT('+SAPBR=0,1')
    return date_time


# # TLS Certificates Check - Check state on Simcom of TLS certificates.
# def certs_check():
#     print("++++++++++++++++++++ CERTS - CHECK +++++++++++++++++++++\n")
#     AT('+CFSINIT')
#     AT('+CFSGFIS=3,"{}"'.format(ca_name))
#     AT('+CFSGFIS=3,"{}"'.format(cert_name))
#     AT('+CFSGFIS=3,"{}"'.format(key_name))
#     AT('+CFSTERM')
#
#
# # TLS Certificates Load - Load new certificates from flash.
# def certs_load():
#     print("++++++++++++++++++++ CERTS - LOAD +++++++++++++++++++++\n")
#     AT('+CFSINIT')
#     with open(certs_folder + "/" + ca_name) as f:
#         data = f.read()
#         AT('+CFSWFILE=3,"{}",0,{},5000'.format(ca_name, len(data)), success="DOWNLOAD")
#         send(data)
#     with open(os.path.join(certs_folder, cert_name), 'rb') as f:
#         data = f.read()
#         AT('+CFSWFILE=3,"{}",0,{},5000'.format(cert_name, len(data)), success="DOWNLOAD")
#         send(data)
#     with open(os.path.join(certs_folder, key_name), 'rb') as f:
#         data = f.read()
#         AT('+CFSWFILE=3,"{}",0,{},5000'.format(key_name, len(data)), success="DOWNLOAD")
#         send(data)
#     AT('+CFSTERM')
#
#
# # TLS certificates delete - Delete the current certificates.
# def certs_delete():
#     print("++++++++++++++++++++ CERTS - DELETE +++++++++++++++++++++\n")
#     AT('+CFSINIT')
#     AT('+CFSDFILE=3,"{}"'.format(ca_name))
#     AT('+CFSDFILE=3,"{}"'.format(cert_name))
#     AT('+CFSDFILE=3,"{}"'.format(key_name))
#     AT('+CFSTERM')
#
#
# # To test if MQTT is connected and active.
# def is_mqtt_connected():
#     watch(timeout=0)
#     smstate = AT('+SMSTATE?')  # Check MQTT connection state
#     if smstate[1][0].split(":")[1].strip() == "0":
#         return False
#     else:
#         return True
#
#
# # To connect to MQTT service through Simcom.
# def mqtt_connect(mqtt_server=mqtt_server, client_id=client_id, mqtt_user=mqtt_user, mqtt_pass=mqtt_pass):
#     print("++++++++++++++++++++ MQTT - NO SSL +++++++++++++++++++++\n")
#     watch(timeout=0)
#     active = AT("+CNACT?")  # Check connection open and have IP
#     if active[1][0].split(":")[1].strip() == '0,"0.0.0.0"':
#         AT("+CNACT=1")  # Open wireless connection
#     AT('+SMCONF="CLIENTID",' + client_id + '')
#     AT('+SMCONF="KEEPTIME",180')  # Set the MQTT connection time (timeout?)
#     AT('+SMCONF="CLEANSS",1')
#     AT('+SMCONF="USERNAME","' + mqtt_user + '"')
#     AT('+SMCONF="PASSWORD","' + mqtt_pass + '"')
#     AT('+SMCONF="URL","{}","1883"'.format(mqtt_server))  # Set MQTT address
#     smstate = AT('+SMSTATE?')  # Check MQTT connection state
#     if smstate[1][0].split(":")[1].strip() == "0":
#         AT('+SMCONN', timeout=30)  # Connect to MQTT
#         mqtt_sub('t')
#
#
# # To disconnect from MQTT service AND the CNACT data attachment on Simcom.
# def mqtt_disconnect():
#     if is_mqtt_connected() is True:
#         print('Mqtt is connected / disconnecting now.')
#         AT('+SMDISC')
#         if is_mqtt_connected() is True:
#             print('Disconnection was not successfull')
#         else:
#             print('MQTT is disconnected.')
#     active = AT("+CNACT?")  # Check connection open and have IP
#     if active[1][0].split(":")[1].strip() != '0,"0.0.0.0"':
#         print('CNACT is active closing now.')
#         AT("+CNACT=0")
#         print('CNACT disconnected.')
#
#
# # Subscribe to a MQTT topic via Simcom
# def mqtt_sub(topic):
#     watch(timeout=0)
#     if is_mqtt_connected() is True:
#         AT('+SMSUB="' + topic + '",1')
#         watch(timeout=0)
#     else:
#         print('MQTT not connected... Connecting now')
#         mqtt_connect()
#         AT('+SMSUB="' + topic + '",1')
#
#
# # Publish to a topic via Simcom.
# def mqtt_pub(topic, msg):
#     watch(timeout=0)
#     if is_mqtt_connected() is True:
#         AT('+SMPUB="' + topic + '","{}",1,1'.format(len(msg)), timeout=30, success=">")  # Publish command
#         send(msg.encode('utf-8'))
#         print(msg)
#         watch(timeout=2)
#     else:
#         print('MQTT not connected')
#         mqtt_connect()
#         mqtt_pub(topic, msg)
#
#
# # MQTT callback from Simcom - What to do when receiving message.
# def mqtt_callback(r):
#     global mqtt_msg
#     global mqtt_new
#     print('In MQTT Callback')
#     topic = r[0].strip('"')
#     msg = r[1].strip('"')
#     print('Topic is: ' + topic)
#     print('Message is: ' + msg)
#     mqtt_msg = msg
#     mqtt_new = True
#
#
# # Simple Connection for testing TCP.
# def tcp():
#     AT('+CIPSTART="TCP","138.197.128.162","1883"')
