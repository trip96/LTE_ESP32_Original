#########################################################
#####   Encoding Scheme for reducing decimal data   #####
#########################################################

"""
Encoding scheme for reducing the payloads of MQTT data. Because MQTT sends plain text we have converted our temperatures
to ASCII characters reducing the number of bytes sent over networks using MQTT. This is useful to conserve data on
cellular IoT plans and to reduce energy demands on battery operated devices. For our purposes we also encode every
decimal value with two printable ASCII characters giving us base 92 numbering system using the 92 printable ASCII
characters. This gives a max range of [0 to 8463]. Using the decimal offset you can encode negative numbers as well.
"""

#############################################
#####   Constants and Configurations    #####
#############################################

ascii_offset = 34           # In order to get to printable characters we need to skip the control chars.
encoding_base = 92          # The remaining 92 characters give us a base of 92 for encoding.
decimal_offset = -999       # Decimal offset can be anything. Set to lowest value (negatives accepted) to encode.


###############################
#####   Decimal To ASCII  #####
###############################


def d2a(data):
    global ascii_offset
    global encoding_base
    global decimal_offset

    if data is not None:
        # print('DATA IS : ' + str(data))
        # print(type(data))
        if d2a_range_check(data):
            return d2a_range_check(data)

        absolute_decimal = data - decimal_offset

        lsc = absolute_decimal % encoding_base
        msc = int(absolute_decimal / encoding_base)

        encoded = chr(msc + ascii_offset) + chr(lsc + ascii_offset)

        return encoded

    else:
        pass
        # print('DATA DEBUG: ')
        # print(str(data))


#################################
#####   ASCII to Decimal    #####
#################################


def a2d(data):
    global ascii_offset
    global encoding_base
    global decimal_offset

    if a2d_range_check(data):
        return a2d_range_check(data)

    lsc = int(ord(data[1]) - ascii_offset)
    msc = int(ord(data[0]) - ascii_offset)

    absolute = (int(msc) * (encoding_base ** 1)) + (int(lsc) * (encoding_base ** 0))

    decimal = absolute + decimal_offset

    return decimal


def d2a_range_check(data):
    if data > (8463 + decimal_offset):
        # raise ValueError('Number to be encoded exceeds range - HIGH')
        return '~~'

    elif data < decimal_offset:
        # raise ValueError('Number to be encoded exceeds range - LOW')
        return '!!'
    else:
        pass


def a2d_range_check(data):
    if data == '!!':
        # raise ValueError('Number to be encoded exceeds range - HIGH')
        return -10000
    elif data == '~~':
        # raise ValueError('Number to be encoded exceeds range - LOW')
        return 10000


#######################################
#####   Delta Minutes Seconds     #####
#######################################

def time_delta(start_time, time, status):
    ascii_offset = 65

    delta = time - start_time

    minutes, seconds = divmod(delta, 60)
    encoded_minutes = chr(ascii_offset + int(minutes))

    if status == 0:
        encoded_minutes = encoded_minutes.lower()
    else:
        encoded_minutes = encoded_minutes.upper()

    encoded_seconds = chr(ascii_offset + int(seconds))
    return encoded_minutes+encoded_seconds
