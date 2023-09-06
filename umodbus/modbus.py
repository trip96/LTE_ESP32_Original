
from umodbus import functions
from umodbus import const as Const
import struct
from machine import UART
import time


class Modbus:

    def __init__(self):

        global s
        # UART 1 used for Cellular modem chip.
        s = UART(2, 9600)  # init with given baudrate
        # rx=16, tx=17 for non cell ESP32. RX=22, TX=23 for cellular chips. 32 & 33 can also be used.
        # pins 22 and 23 work for RX - TX pins 12 and 14 work as well.
        s.init(baudrate=9600, bits=8, parity=None, stop=1, rx=32, tx=33)  # init with given parameters

    def _calculate_crc16(self, data):
        crc = 0xFFFF
        for char in data:
            crc = (crc >> 8) ^ Const.CRC16_TABLE[((crc) ^ char) & 0xFF]
        return struct.pack('<H', crc)

    def _bytes_to_bool(self, byte_list):
        bool_list = []
        for index, byte in enumerate(byte_list):
            bool_list.extend([bool(byte & (1 << n)) for n in range(8)])
        return bool_list

    def _to_short(self, byte_array, signed=True):
        response_quantity = int(len(byte_array) / 2)
        fmt = '>' + (('h' if signed else 'H') * response_quantity)
        return struct.unpack(fmt, byte_array)

    def _exit_read(self, response):
        if response[1] >= Const.ERROR_BIAS:
            if len(response) < Const.ERROR_RESP_LEN:
                return False
        elif (Const.READ_COILS <= response[1] <= Const.READ_INPUT_REGISTER):
            expected_len = Const.RESPONSE_HDR_LENGTH + 1 + response[2] + Const.CRC_LENGTH
            if len(response) < expected_len:
                return False
        elif len(response) < Const.FIXED_RESP_LEN:
            return False
        return True

    def _uart_read(self):
        time.sleep_ms(100)
        read = s.read()
        return read

    def _send_receive(self, modbus_pdu, slave_addr):
        serial_pdu = bytearray()
        serial_pdu.append(slave_addr)
        serial_pdu.extend(modbus_pdu)
        crc = self._calculate_crc16(serial_pdu)
        serial_pdu.extend(crc)
        s.write(serial_pdu)
        return self._uart_read()

    def read_holding_registers(self, slave_addr, starting_addr, register_qty, signed=True):
        try:
            starting_addr = int(str(starting_addr), 16)
            modbus_pdu = functions.read_holding_registers(starting_addr, register_qty)
            resp_data = self._send_receive(modbus_pdu, slave_addr)
            register_value = self._to_short(resp_data, signed)
            return register_value[3]  # can use / 10 if we need to divide by 10
        except Exception as ex:
            # return 'Error Reading: ' + str(ex)        # DEBUG
            return None

    def write_single_register(self, slave_addr, register_address, register_value, signed=True):
        register_address = int(str(register_address), 16)
        modbus_pdu = functions.write_single_register(register_address, register_value, signed)
        resp_data = self._send_receive(modbus_pdu, slave_addr)
        return resp_data[3]

    def init(self):
        s.init(9600)

    def deinit(self):
        s.deinit()
