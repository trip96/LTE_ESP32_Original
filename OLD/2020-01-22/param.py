#############################################################################################
#####   Parameters for Ascon Controllers - Y39 and X34 - Constants for Modbus Registers #####
#############################################################################################

"""
This file contains the distinct modbus addresses for ascon.querying the Ascon controllers. Currently we are using two
controllers (Jan 2020) that have different register addresses for their respective parameters. This file is loaded
depending on the value returned by the ascon.py get_rcu_info(): . That functions determines what controller we are
interacting with and then loads the corresponding class from this file. All parameters are loaded then called via
a constant variable in the ascon.py file (param.pr_1).
"""

#################################
#####   Controller Classes  #####
#################################


class Y39:
    # Class of modbus parameters specific to the Y39 Ascon controller.

    # Temperature Long Polling.
    cabinet_temp = '200'
    evap_temp = '201'

    # Short Polling Status.
    compressor_status = '210'
    defrost_status = '211'
    door_status = '20E'

    # Param capture registers.
    set_point = '2801'
    high_temp_thresh = '282E'
    high_temp_delay = '2831'
    restock_duration = '2845'
    high_temp_defrost_delay = '2834'
    rcu_memory_error = '299'
    startup_timer = '230'
    ht_power_up_timer = '232'
    ht_timer = '231'
    ht_defrost_timer = '233'
    ht_restocking_timer = '235'
    door_open_alarm_delay = '2836'
    restocking_delay = '2845'
    buzzer = '290'
    firmware_release = ['CF12', 'CF13']

    # Temp Units
    temp_units = '2809'
    
    # Alert Mask
    alert_mask = '207'


class X34:
    # Class of modbus parameters specific to the X34 Ascon controller.

    # Temperature Long Polling.
    cabinet_temp = '200'
    evap_temp = '201'

    # Short Polling Status.
    compressor_status = '210'
    defrost_status = '211'
    door_status = '220'

    # Param capture registers.
    set_point = '2802'
    high_temp_thresh = '283D'
    high_temp_delay = '2840'
    restock_duration = '244'
    high_temp_defrost_delay = '284A'
    rcu_memory_error = '299'
    startup_timer = '283B'
    ht_power_up_timer = '2848'
    ht_timer = '2840'
    ht_defrost_timer = '284A'
    ht_restocking_timer = '2861'
    door_open_alarm_delay = '247'
    restocking_delay = '244'
    buzzer = '290'
    temp_units = '2806'
    firmware_release = ['CF12', 'CF13']
    operating_config = '285C'

    # Alert Mask
    alert_mask = '207'
