import msgpack

json = '{'ht_defrost_timer': 45, 'startup_timer': 600, 'rcu_memory_error': 0, 'door_status': 0, 'high_temp_defrost_delay': 45, 'restock_duration': 0, 'set_point': -200, 'temp_units': 1, 'alert_mask': 0, 'high_temp_thresh': 0, 'cabinet_temp': -201, 'ht_power_up_tim
er': 200, 'ht_restocking_timer': 4500, 'defrost_status': 0, 'door_open_alarm_delay': 0, 'high_temp_delay': 3000, 'restocking_delay': 0, 'evap_temp': 500, 'buzzer': 0, 'lock_status': 1, 'compressor_status': 0, 'operating_config': -2, 'ht_timer': 3000}'

encoded = msgpack.packb(json)

print(encoded)
