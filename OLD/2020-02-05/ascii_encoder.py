#########################################################
#####   Encoding Scheme for reducing decimal data   #####
#########################################################

"""
Encoding scheme for reducing the payloads of MQTT data. Because MQTT sends plain text we have converted our temperatures
to ASCII characters reducing the number of bytes sent over networks using MQTT. This is useful to conserve data on
cellular IoT plans and to reduce energy demands on battery operated devices. For our purposes we also encode every
decimal value with two printable ASCII characters giving us base 92 numbering system using the 92 printable ASCII
characters. This gives a max range of 8463. Using the decimal offset you can determine negative numbers as well.
"""

#############################################
#####   Constants and Configurations    #####
#############################################

ascii_offset = 34
encoding_base = 92
decimal_offset = -999


###############################
#####   Decimal To ASCII  #####
###############################


def d2a(data):
    global ascii_offset
    global encoding_base
    global decimal_offset

    absolute_decimal = data - decimal_offset

    lsc = absolute_decimal % encoding_base
    msc = int(absolute_decimal / encoding_base)

    encoded = chr(lsc + ascii_offset) + chr(msc + ascii_offset)

    return encoded


#################################
#####   ASCII to Decimal    #####
#################################


def a2d(data):
    global ascii_offset
    global encoding_base
    global decimal_offset

    lsc = int(ord(data[0]) - ascii_offset)
    msc = int(ord(data[1]) - ascii_offset)

    absolute = (int(msc) * (encoding_base ** 1)) + (int(lsc) * (encoding_base ** 0))

    decimal = absolute + decimal_offset

    return decimal

















# import sys
# import binascii
# from datetime import datetime
#
#
# now = datetime.now()
# current_time = now.strftime("%Y-%m-%d-%H:%M:%S")
# print("Current Time =", current_time)
# rcu_data = [174, 86]
#
#
# def encode(data):
#     # encoded_msg = []
#     # for i in data:
#     #     if i <= 0:
#     #         i = abs(i)
#     #         print(i)
#     #         i = i + 63
#     #     chr(int(63))
#     #     encoded_msg.append(chr(i+63))
#     #     print(encoded_msg)
#     year = datetime.now().strftime("%y")
#     month = datetime.now().strftime("%m")
#     day = datetime.now().strftime("%d")
#     hour = datetime.now().strftime("%H")
#     minute = datetime.now().strftime("%M")
#     second = datetime.now().strftime("%S")
#     # print(second)
#     # print(minute)
#     print(hour)
#     # print(day)
#     # print(month)
#     # print(year)
#     ascii_offset = 63
#     number = 13
#     # print(chr((int(ascii_offset) + int(number))))
#     # payload = ''
    payload = 'T' + chr(ascii_offset + int(year)) + chr(ascii_offset + int(month)) + chr(ascii_offset + int(day)) + \
              chr(ascii_offset + int(day)) + chr(ascii_offset + int(hour)) + chr(ascii_offset + int(minute)) + \
              chr(ascii_offset + int(second))
    print(payload)
#
#     # decoded = str(ord(payload[1])) - ascii_offset) + ',')
#     # print(decoded)
#     decoded = [(int(ord(payload[1]) - ascii_offset)), (int(ord(payload[2]) - ascii_offset)),
#                (int(ord(payload[3]) - ascii_offset)), (int(ord(payload[4]) - ascii_offset)),
#                (int(ord(payload[5]) - ascii_offset)), (int(ord(payload[6]) - ascii_offset)),
#                (int(ord(payload[7]) - ascii_offset))]
#     print(str(decoded))
#     # print(str(ord((chr(ascii_offset + int(year)))) - ascii_offset) + ',')
#
#
# encode(rcu_data)
#
#
# def enclode():
#     print(hex(rcu_data[0]))
#     print(hex(rcu_data[1]))
#     new_msg = [hex(rcu_data[0])].append(hex(rcu_data[1]))
#     # print('Length of new msg ' + str(new_msg) + ' is ' + str(sys.getsizeof(new_msg)))
#
#
# # enclode()
# #
# #
# # def encloose():
# #     print(''.join('{:02x}'.format(x) for x in rcu_data))
# #     print(binascii.hexlify(bytes(rcu_data)))
# #
# # encloose()
#
# alert_mask = '127'  # Simulated result of register with bitmask alert
# scale = 16  # equals to hexadecimal
# num_of_bits = 16 # how many bits the register contains
# binary = (bin(int(alert_mask, scale))[2:].zfill(num_of_bits)) #conversiont binary
#
# print ('Binary Number is ' + binary)
#
# pos = 2
#
# print('Bit position: ' + str(pos) + ' in alert is: ' + binary[15-pos])
