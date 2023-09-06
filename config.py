##################################################################################################
##### Configuration for Minus Forty Ascon RCU IoT Gateway Developed mostly by chya boi Kinno #####
##################################################################################################

""" This is a file that holds all the configuration paramenters for Minus Forty IoT development gateway
In here you will find Simsom modem settings, APN settings, MQTT settings, Ascon Controller Settings """

####################################
#####   Main Program Settings  #####
####################################

frequent_poll_interval = 3
long_poll_interval = 60
send_interval = 600


#############################
#####   MQTT Settings   #####
#############################

# MQTT Settings

mqtt_server = '138.197.128.162'
mqtt_port = '1883'
client_id = '003'
mqtt_user = 'LTE-Test'
mqtt_pass = 'spiderman'


##############################
#####   Simcom Settings ######
##############################

# Cellular Network Setup

apn = 'm2minternet.apn'
rx = 26
tx = 27

# TLS Certificates Configuration

certs_folder = 'certs'
ca_name = 'mqtt-ca.crt'
cert_name = "mqt.crt"
key_name = "mqtt.key"

#############################
#####   Ascon Settings  #####
#############################

