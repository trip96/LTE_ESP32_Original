#############################################################################################################
##### Custom module written to provide functions and methods for ASCON RCU's as used by Minus Forty     #####
#############################################################################################################

"""
This is a custom module written to provide custom methods and functions for the Acon controller as used by Minus
Forty Technologies. These methods and functions are not supported outside of the Minus Forty ecosystem and these
modules are based on custom implementations of other open source modules. This may cause confusion and any
malfunctions are not warrantied by Minus Forty or Kinno
"""

#########################
#####   Imports     #####
#########################

import gc
import utime
from umodbus.modbus import Modbus


#####################################################################
##### Setup and Config for Ascon RCU in relation to ESP32 UART  #####
#####################################################################

# Custom SOCK for UART connection with 'FF' filter.
s = Modbus()    # Modbus.py takes care of the protocol. Modified for our FF problem.

# Collect Garbage to keep memory clean
gc.collect()

# Global Variables for frequent polling to store.
door_previous = [0]         # Set the door to closed on initial startup.

frequent_poll_data = {}     # Have blank dictionary created for storing data from polling.

#################################################
##### Tools and Functions For ASCON RCU     #####
#################################################


# Deinit For shutting down and restarting.
def init():
    s.init()      # Denit passed into Modbus.py Moodbus.py sets up the UART.


# Deinit For shutting down and restarting.
def deinit():
    s.deinit()      # Denit passed into Modbus.py Moodbus.py sets up the UART.


# For Writing to the Ascon RCU via Modbus. Comes form MQTT messages.
def write_register(register_address, value):

    try:
        payload = s.write_single_register(slave_addr=int(1), register_address=register_address,
                                          register_value=int(value))
        return payload

    except ValueError as e:
        # Error Reporting.
        print("Hex Parameter: " + value + " NOT recognized by Controller")
        print(str(e))
        pass

    except Exception as e:
        # Error Reporting. Broad error catch.
        print('Error in Writting Register ASCON module.')
        print(str(e))
        pass


# General Query function for getting values from RCU
def query_rcu(send_data_list, signed=True):

    update_values = []      # List to hold the values returned from send data list.
    for i in range(len(send_data_list)):
        try:
            payload = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1), signed=signed)     # Query the RCU.

            # Adding Returned values to make a list of all values at end of polling loop.
            update_values = update_values + [payload]   # Might be better to 'update_values.append(payload)'

        except ValueError as e:
            # Error Reporting.
            print("Hex Parameter: " + send_data_list[i] + " NOT recognized by Controller")
            print(str(e))
            pass

        except IOError as e:
            # Error Reporting.
            print('I/O error - Device slave ID NOT found')
            print(str(e))
            pass
        except Exception as e:
            # Error Reporting.
            print('Other Error in Reading Register from RCU.')
            print(e)
            pass
    # Return the full list of values from controller.
    return update_values


# Temperature Function
def get_temperatures():

    temperatures_list = [param.cabinet_temp, param.evap_temp]       # Hex addresses from param.py
    return query_rcu(temperatures_list)                             # Query the RCU and return values.


# Frequent Polling operations
def frequent_polling():

    global frequent_poll_data       # Global to hold our returns

    try:

        # Door Status query - Get status of the door right now.
        door_now = query_rcu([param.door_status])[0]  # Query the RCU for the current door status.
        utime.sleep_ms(200)     # Give time for Ascon RCU before next question.

        frequent_poll_data = {'door_status': door_now}      # Add door status to the frequent poll data return.

        # Defrost Status - Get status of defrost right now.
        # defrost_status = query_rcu([param.defrost_status])[0]  # Query the RCU for the current defrost status.
        # utime.sleep_ms(200)     # Give time for Ascon RCU before next question.
        # frequent_poll_data['defrost_status'] = defrost_status  # Add defrost status to the frequent poll data return.

        get_alert_status()      # Query the Alert Register.

        return frequent_poll_data

    except Exception as e:
        print('Error in Frequent Polling! - ASCON MODULE')
        print(e)
        pass


# Alert Management
def get_alert_status():     # TODO have this return values NOT use global dictionary.

    global frequent_poll_data

    # Alerts
    utime.sleep_ms(200)
    alert_mask = query_rcu([param.alert_mask], signed=False)  # Alert Mask - Signed false as it returns mask.
    utime.sleep_ms(200)
    # print('RAW ALERT MASK IS: ' + str(alert_mask))    # DEBUG

    # Check for errors, bad returns, known non-responses (Type None or String).
    if type(alert_mask[0]) is int and alert_mask[0] > 0:    # make sure the return is usable.

        # Turn decimal returned to bitmask using function.
        alert_mask = dec_to_bitmask(alert_mask[0])      # Convert the decimal response to the bitrange we can use.
        # print('ALERT MASK IS: ' + alert_mask)     # For debugging the alert mask conversion.

        # High-Temp Alert
        if alert_mask[6] == '1':  # TODO Have separate params for X34 and Y39 bitmask params.
            # print('High Temp Alert')
            frequent_poll_data['high_temp_alert'] = 'yes'
            # alert('high_temp')
        if alert_mask[6] == '0':
            frequent_poll_data['high_temp_alert'] = 'no'
            # print('NO - High Temp Alert')

        # Low Temp Alert
        if alert_mask[5] == '1':
            # print('Low Temp Alert')
            frequent_poll_data['low_temp_alert'] = 'yes'
            # alert('high_temp')
        if alert_mask[5] == '0':
            frequent_poll_data['low_temp_alert'] = 'no'
            # print('NO - Low Temp Alert')

        # Door Open Alert
        if alert_mask[4] == '1':
            # print('Door Open Alert')
            frequent_poll_data['door_open_alert'] = 'yes'
            # alert('high_temp')
        if alert_mask[4] == '0':
            frequent_poll_data['door_open_alert'] = 'no'
            # print('NO Door Open Alert')
        else:
            print('Negative RCU alert mask.')
            pass
    else:
        frequent_poll_data['high_temp_alert'] = 'no'
        frequent_poll_data['low_temp_alert'] = 'no'
        frequent_poll_data['door_open_alert'] = 'no'

    # Malfunctioning Alert
    mem_err = query_rcu(['299'])
    # print(mem_err)
    if mem_err[0] == 1:
        # print('Memory Error')
        frequent_poll_data['malfunctioning_alert'] = 'yes'
        # alert('high_temp')
    if mem_err[0] == 0:
        frequent_poll_data['malfunctioning_alert'] = 'no'
        # print('NO - Memory Error')

        # TODO Power Out Alert
        # TODO Check GPIO for voltage


# Converts decimal value returned by RCU to bitmask to then compare for active alerts.
def dec_to_bitmask(decimal_value):
    num_of_bits = 16  # Zfill number of total bits in bitmask.
    alert_mask = bin(decimal_value)[2:]     # Convert to Binary and strip the string b'
    alert_mask = zfill(alert_mask, num_of_bits) # Use zfill function to fill out preceding 0's
    return alert_mask


# Get controller information
def get_rcu_serial():
    try:
        send_data_list = ['CF44', 'CF43', 'CF42']       # The serial number located in these register.

        serial_number_hex = ''      # Set the string container for the serial number.

        for i in range(len(send_data_list)):
            try:
                pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                                   register_qty=int(1))
                hex_serial = hex(int(pay_load))     # Convert the payload

                serial_number_hex = serial_number_hex + hex_serial[2:]      # Add the results together.

            except Exception as e:
                print("Error Communicating with RCU for determining Serial Number.")
                print(str(e))
                pass
        # serial_number = int.from_bytes(str.encode(serial_number_hex), byteorder=sys.byteorder)
        serial_number = str(int(serial_number_hex, 16))
        return str(serial_number)
    except Exception as e:
        print('Error Getting RCU Serial.')
        print(e)


def get_rcu_fw():
    send_data_list = ['CF12', 'CF13']       # Firmware located in these registers.
    payload = 'N/A'                         # Payload set to N/A

    for i in range(len(send_data_list)):
        try:
            payload = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))
        except Exception as e:
            print("Error in determining the Firmware version of RCU.")
            print(str(e))
            pass

    return payload


# RCU name
def get_rcu_type():
    send_data_list = ['CF38', 'CF39', 'CF3A', 'CF3B']       # RCU name contained in these registers.
    product_code = ''

    for i in range(len(send_data_list)):
        try:
            pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))
            if pay_load == 0:
                break
            else:
                pass

            letter = convert_to_ascii(pay_load)             # Convert the result to a letter.
            product_code = product_code + str(letter)       # Add em up!


        except Exception as e:
            print('Error Retrieving RCU Type. RCU not communicating or no register exist for model type.')
            print(e)
            return 'RCU Not Recognized'
            pass
    return product_code


# Param Pull
def get_rcu_param():

    # Using the python dir to collect all variables in the class. Except built in namespaces ('__').
    param_list = [a for a in dir(param) if not a.startswith('__')]

    rcu_param_list = []     # Set up list for holding parameters from param.py (param_list).
    rcu_query_list = []     # Set up list for holding the query to be sent to RCU.

    for i in param_list:                        # cycle through the parameters from dir(param).
        rcu_param_list.append('param.' + i)     # append each parameter into a list.

    for i in rcu_param_list:                    # Make the string into a variable using eval().
        rcu_query_list.append(eval(i))          # append the variable to the list to be sen to RCU.

    rcu_param_results = query_rcu(rcu_query_list)       # Query the RCU.

    rcu_dictionary = {}                                 # Empty dictionary to hold the response from RCU.
    x = 0
    for i in param_list:
        rcu_dictionary[i] = rcu_param_results[x]        # combine the name and the value again for dictionary.
        x = x + 1

    return rcu_dictionary


# Smart lock 2 check.
def is_smart_lock_2():
    if query_rcu([2853]) == 4:
        if query_rcu([2855]) == 4:
            return True
        else:
            return False
    else:
        return False


# Celsius or Fahrenheit
def is_celsius():
    if query_rcu(param.temp_units) is 0:
        return True
    else:
        return False


# Convert to ascii from hex.                    #TODO Split into 'tools' module
def convert_to_ascii(dec_to_ascii):
    return chr(int(dec_to_ascii))


#  Fill the 0's for bitmask for alert return    #TODO Split into 'tools' module
def zfill(s, width):
    return '{:0>{w}}'.format(s, w=width)


# Load the Correct Constants for Ascon modbus Registers from param.py
attempts = 0
while attempts < 3:
    try:
        if get_rcu_type()[0] is 'T':
            from param import Y39 as param
            print('Y39 Controller Detected!')
        elif get_rcu_type()[0] is 'Y':
            from param import Y39 as param
            print('Y39 Controller Detected!')
        elif get_rcu_type()[0] is 'X':
            from param import X34 as param
            print('X34 Controller Detected!')
        else:
            print('RCU Type Not recognized. It is neither X34 / Y39 type RCU, OR, can not communicate.')
    except Exception as e:
        print('Can Not Determine RCU Type. Waiting 10 Seconds and Trying Again.')
        print(e)
        attempts = attempts +1
        utime.sleep(10)
