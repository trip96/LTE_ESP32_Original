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
import time                     # Time module for sleeping.
import gc                       # Garbage Collection for keeping memory clean.


# Collect garbage after imports to keep things clean.
gc.collect()

####################################################################
##### SETUP AND CUSTOMIZATION FOR SIMCOM APN AND MQTT SETTINGS #####
####################################################################


# # Cellular Network Setup
#
# apn = 'm2minternet.apn'                 # Cellular network APN
#
# # Setting up UART to SIMCOM 7000 chip.
#
# # Initialization at start.
# simcom = UART(1, 9600)  # init with given baudrate
# simcom.init(baudrate=9600, bits=8, parity=None, stop=1, rx=26, tx=27)  # init with given parameters check rx and tx.


cell_power = Pin(4, Pin.OUT)    # PIN 4 on ESP32 controls power of Simcom.