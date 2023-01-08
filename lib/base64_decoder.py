# Can't use Micropython's standard base64 library because of memory allocation errors.
# Even with more than 100 kilobytes available and only 20 kilobytes of data, this will crash:
# bytes(binascii.a2b_base64(bytes(input_buffer[0: buffer_index]).decode('ascii')))
def base64_value(c):
    if c >= 65 and c < 91: # A-Z
        return c - 65
    if c >= 97 and c < 123: # a-z
        return 26 + (c - 97)
    if c >= 48 and c <= 58: # 0-9
        return 52 + (c - 48)
    if c == 43:
        return 62
    if c == 47:
        return 63
    return -1 # equals
    
# Returns number of decoded bytes (usually 3 if no padding)
def decode_single(four_in, three_out):
    in_1 = base64_value(four_in[0])
    in_2 = base64_value(four_in[1])
    in_3 = base64_value(four_in[2])
    in_4 = base64_value(four_in[3])
    three_out[0] = ((in_1 & 0x3F) << 2) | (in_2 >> 4)
    three_out[1] = 0
    three_out[2] = 0
    if in_3 == -1:
        return 1
    three_out[1] = ((in_2 & 0x0F) << 4) | (in_3 >> 2)
    if in_4 == -1:
        return 2
    three_out[2] = ((in_3 & 0x03) << 6) | in_4
    return 3

def base64_decode(input_buf, output_buf, input_length):
    bytes_decoded = 0
    for i in range(0, input_length // 4):
        input_index = 4 * i
        bytes_decoded += decode_single(input_buf[4 * i : 4 * (i + 1)], output_buf[bytes_decoded : bytes_decoded + 3])
    return bytes_decoded
