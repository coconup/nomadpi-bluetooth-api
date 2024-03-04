import crcmod

def bytes_to_int(bs, offset, length, signed=False, scale=1):
    try:
        byte_order = 'big' if length > 0 else 'little'
        byte_slice = bs[offset:offset + length] if length > 0 else bs[offset + length + 1:offset + 1]
        result = int.from_bytes(byte_slice, byteorder=byte_order, signed=signed)
        return round(result * scale, 2)
    except IndexError:
        return 0

def int_to_bytes(i, pos = 0):
    return [
        int(format(i, '016b')[:8], 2),
        int(format(i, '016b')[8:], 2)
    ]

def crc16_modbus(data: bytes):
    crc_func = crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000)
    crc_value = crc_func(data)
    crc_bytes = crc_value.to_bytes(2, byteorder='little')
    return crc_bytes

def deep_remove_nan(input_hash):
    if isinstance(input_hash, dict):
        result = {}
        for key, value in input_hash.items():
            if isinstance(value, dict) or isinstance(value, list):
                parsed_value = deep_remove_nan(value)
                if parsed_value:
                    result[key] = parsed_value
            elif value != None and value == value:  # Check if value is not NaN (using the fact that NaN != NaN)
                result[key] = value
        return result
    elif isinstance(input_hash, list):
        return [deep_remove_nan(item) for item in input_hash]
    else:
        return input_hash