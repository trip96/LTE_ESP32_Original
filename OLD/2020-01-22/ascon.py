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
s = Modbus()

# Collect Garbage to keep memory clean
gc.collect()

# Global Variables for frequent polling to store. Only sending data every minute.
door_openings = 0
door_previous = [0]
door_open_time = 0
compressor_on_time = 0
frequent_poll_data = {}

#################################################
##### Tools and Functions For ASCON RCU     #####
#################################################


# Convert to ascii tool
def convert_to_ascii(dec_to_ascii):
    return chr(int(dec_to_ascii))


# General Query function for getting values from RCU
def query_rcu(send_data_list):
    # Empty list in order to gather all the values returned.
    update_values = []
    for i in range(len(send_data_list)):
        try:
            pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))

            # Adding Returned values to make a list of all values at end of polling loop.
            update_values = update_values + [pay_load]

            # print(pay_load)

        except ValueError as ex:
            # Error Reporting.
            print("Hex Parameter: " + send_data_list[i] + " NOT recognized by Controller")
            print(str(ex))
            pass

        except IOError as ex:

            # Error Reporting.
            print('I/O error - Device slave ID NOT found')
            print(str(ex))
            pass
    # Return the full list of values from controller.
    return update_values


# Temperature Function
def get_temperatures():

    temperatures_list = [param.cabinet_temp, param.evap_temp]
    return query_rcu(temperatures_list)


# Frequent Polling operations
def frequent_polling():
    global door_openings
    global door_previous
    global door_open_time
    global compressor_on_time
    global frequent_poll_data

    try:

        now = utime.time()

        # DOOR POLLING RCU query
        door_now = query_rcu([param.door_status])[0]  # Y39 uses 20E for digital status.

        frequent_poll_data = {'door_status': door_now}
        # Checking to see if door status has changed
        if door_now != door_previous:  # Check if door has completed open and close cycle.
            door_openings = door_openings + 1

        #
        # door_previous = door_now
        # # Keeping tabs on how long the door is in a '1' state - OPEN state.
        # if door_now == [1]:
        #     # door_open_time = door_open_time + 3  # Assuming door is open whole length.

        # Compressor Status
        compressor_status = query_rcu([param.compressor_status])[0]
        frequent_poll_data['compressor_status'] = compressor_status

        # Defrost Status

        defrost_status = query_rcu([param.defrost_status])[0]
        frequent_poll_data['defrost_status'] = defrost_status

        # Alerts
        alert_mask = query_rcu([param.alert_mask])  # Y39
        if alert_mask[0] != 0:
            scale = 16  # equals to hexadecimal
            num_of_bits = 16
            bin(int(alert_mask, scale))[2:].zfill(num_of_bits)

            # High-Temp Alert
            if alert_mask[5] == 1:
                print('High Temp Alert')
                frequent_poll_data['high_temp_alert'] = 'yes'
                # alert('high_temp')
            else:
                frequent_poll_data['high_temp_alert'] = 'no'


            # Low Temp Alert
            if alert_mask[6] == 1:
                print('Low Temp Alert')
                frequent_poll_data['low_temp_alert'] = 'yes'
                # alert('high_temp')
            else:
                frequent_poll_data['low_temp_alert'] = 'no'

            # Door Open Alert
            if alert_mask[7] == 1:
                print('Door Open Alert')
                frequent_poll_data['door_open_alert'] = 'yes'
                # alert('high_temp')
            else:
                frequent_poll_data['door_open_alert'] = 'no'

            # Malfunctioning Alert
            if query_rcu(['299']) == 1:
                print('Memory Error')
                frequent_poll_data['malfunctioning_alert'] = 'yes'
                # alert('high_temp')
            else:
                frequent_poll_data['malfunctioning_alert'] = 'no'
        else:
            print('No Alerts from Mask')
            frequent_poll_data['high_temp_alert'] = 'no'
            frequent_poll_data['low_temp_alert'] = 'no'
            frequent_poll_data['door_open_alert'] = 'no'
            frequent_poll_data['malfunctioning_alert'] = 'no'

            # Power Out Alert
            # Check GPIO for voltage

        return frequent_poll_data

    except:
        pass


# Alerts Management

def alert(alert):
    msg = 'alert:' + alert
    print(msg)


# Get controller information
def get_rcu_serial():
    send_data_list = ['CF44', 'CF43', 'CF42']

    serial_number_hex = ''

    for i in range(len(send_data_list)):
        try:
            pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))
            hex_serial = hex(int(pay_load))

            serial_number_hex = serial_number_hex + hex_serial[2:]

        except ValueError as e:
            print("Hex Parameter: " + send_data_list[i] + " NOT recognized by Controller")
            print(str(e))

            pass
        except IOError as e:

            print('I/O error - Device slave ID NOT found')
            print(str(e))
            pass
    # serial_number = int.from_bytes(str.encode(serial_number_hex), byteorder=sys.byteorder)
    serial_number = str(int(serial_number_hex, 16))
    return str(serial_number)


def convert_hex_to_ascii(h):
    chars_in_reverse = []
    while h != 0x0:
        chars_in_reverse.append(chr(h & 0xFF))
        h = h >> 8

    chars_in_reverse.reverse()
    return ''.join(chars_in_reverse)


def get_rcu_fw():
    send_data_list = ['CF12', 'CF13']
    product_code = ''

    for i in range(len(send_data_list)):
        try:
            pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))
            # if pay_load == 0:
            #     break
            # else:
            #     pass
            # # print('Converting : ' + str(pay_load) + " to " + str(letter))
            # product_code = product_code + str(pay_load[0])
            # print(convert_hex_to_ascii(product_code))
            # # print('PRODUCT CODE IS NOW : ' + str(product_code))

        except ValueError as e:
            print("Hex Parameter: " + send_data_list[i] + " NOT recognized by Controller")
            print(str(e))
            pass

        except IOError as e:
            print('I/O error - Device slave ID NOT found')
            print(str(e))
            pass

    return pay_load


# RCU name
def get_rcu_type():
    send_data_list = ['CF38', 'CF39', 'CF3A', 'CF3B']
    product_code = ''

    for i in range(len(send_data_list)):
        try:
            pay_load = s.read_holding_registers(starting_addr=send_data_list[i], slave_addr=int(1),
                                               register_qty=int(1))
            if pay_load == 0:
                break
            else:
                pass

            letter = convert_to_ascii(pay_load)
            # print('Converting : ' + str(pay_load) + " to " + str(letter))
            product_code = product_code + str(letter)
            # print('PRODUCT CODE IS NOW : ' + str(product_code))

        except ValueError as e:
            print("Hex Parameter: " + send_data_list[i] + " NOT recognized by Controller")
            print(str(e))

            pass
        except IOError as e:

            print('I/O error - Device slave ID NOT found')
            print(str(e))
            pass
    return product_code


# Param Pull
def param_pull():
    return query_rcu([param.cabinet_temp, param.evap_temp, param.set_point, param.high_temp_thresh,
                      param.high_temp_delay, param.restock_duration, param.high_temp_defrost_delay,
                      param.rcu_memory_error, param.startup_timer, param.ht_power_up_timer, param.ht_timer,
                      param.ht_defrost_timer, param.ht_restocking_timer, param.door_open_alarm_delay,
                      param.restocking_delay, param.buzzer, param.firmware_release[0], param.firmware_release[1],
                      param.temp_units, param.alert_mask])


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
    if query_rcu(param.temp_units) is 0:  # Y39
        return True
    else:
        return False

# from param import X34 as param  #TODO
# Load the Correct Constants for Ascon modbus Registers from param.py
if get_rcu_type()[0] is 'T':
    from param import Y39 as param
elif get_rcu_type()[0] is 'Y':
    from param import Y39 as param
elif get_rcu_type()[0] is 'X':
    from param import X34 as param
else:
    print('RCU Type Not recognized. It is neither X34 or Y39 type RCU, Or, can not communicate.')

# # RCU serial
# rcu_serial = get_rcu_serial()
