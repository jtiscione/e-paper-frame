from micropython import mem_info
from machine import Pin
import sys
import os
import network
import socket
import time
import gc
import re
import random
import framebuf # For displaying status text messages

import rp2 # RP-2040

from bootstrap_wifi import bootstrap_wifi
from epd import EPD_2in9_B, EPD_3in7, EPD_5in65, EPD_7in5_B

print('STARTING...')
mem_info()

# First- figure out what device we're using and what country we're in
device = 'EPD_5in65' # Let's assume we're using the 7 color display by default...
country = 'US'       # and of course
try:
    with open('./device.txt', 'r') as device_txt:
        device_lines = device_txt.read()
        for line in device_lines.split("\n"):
            hashpos = line.find('#')
            uncommented_line = line if hashpos == -1 else line[0: hashpos]
            device_match = re.search('device\s*=\s*\"?(\w+)\"?', uncommented_line)
            if (device_match is not None):
                device = device_match.group(1)
            country_match = re.search('country\s*=\s*\"?(\w\w)\"?', uncommented_line)
            if (country_match is not None):
                country = country_match.group(1)
        device_lines = None
except:
    print('Could not find/parse device.txt.')

print('device', device)
print('country', country)

rp2.country(country)

# General setup

# USER BUTTONS - These are completely optional.
button_0 = None # If pushed, will display IP address on display
button_1 = None # Push to call sys.exit()
button_2 = None # Push call machine.reset()

if device == 'EPD_5in65':
    # The 5.65 inch display has three buttons mounted on the PCB.
    # These are connected via pull-up resistors to GPIO 15, GPIO 17, and GPIO 2.
    button_0 = Pin(15, Pin.IN, Pin.PULL_UP) # GPIO 15   Display connection info on screen
    button_1 = Pin(17, Pin.IN, Pin.PULL_UP) # GPIO 17   Clear screen
    button_2 = Pin(2, Pin.IN, Pin.PULL_UP)  # GPIO 2  This will trigger invocation of machine.reset()
elif device == 'EPD_7in5_B':
    # The 7.5 inch display has three buttons connected via pull-up resistors to GPIO 2, GPIO 3, and the RUN pin.
    button_0 = Pin(2, Pin.IN, Pin.PULL_UP) # GPIO 2   Display connection info on screen
    button_1 = Pin(3, Pin.IN, Pin.PULL_UP) # GPIO 3   Clear screen
    # button_2 grounds the RUN pin and takes care of itself
# The 4.2 inch display has two buttons connected via pull-up resistors to GPIO 15 and GPIO 17.

# Special function of button_0: if it's being pressed on startup, delete any cached connection info and quit.
if button_1 is not None and button_1.value() == 0:
    try:
        print('Removing last-ip.txt.')
        os.remove('./last-ip.txt')
    except Exception as e:
        print(e)
        pass
    try:
        print('Removing wi-fi.conf.')
        os.remove('./wi-fi.conf')
    except Exception as e:
        pass
    print('Exiting.')
    sys.exit()

# These flags will be checked after every socket timeout while we're waiting for a connection
button_0_flag = False
button_1_flag = False

def callback(pin):
    global button_flag_0, button_flag_1
    if pin == button_0:
        button_0_flag = True
    if pin == button_1:
        button_1_flag = True
    if pin == button_2:
        machine.reset()

if button_0 is not None:
    button_0.irq(trigger=Pin.IRQ_FALLING, handler=callback)
if button_1 is not None:
    button_1.irq(trigger=Pin.IRQ_FALLING, handler=callback)
if button_2 is not None:
    button_2.irq(trigger=Pin.IRQ_FALLING, handler=callback)

# We will have the LED on during startup while it's trying to connect to the network.
# If it cannot connect, the script enters "initial setup mode" and the LED remains on.
# Otherwise, the LED is only lit during interactions with the display.
led = Pin("LED", machine.Pin.OUT)

epd = None
if device == 'EPD_2in9_B':
    epd = EPD_2in9_B()
elif device == 'EPD_3in7':
    epd = EPD_3in7()
elif device == 'EPD_5in65':
    epd = EPD_5in65()
elif device == 'EPD_7in5_B':
    epd = EPD_7in5_B()

def display_lines(*args):
    epd.displayMessage(*args)
    epd.sleep()

led.on()

try:
    wlan, s = bootstrap_wifi(display_lines)
except RuntimeError:
    # Flash SOS to LED indefinitely
    while True:
        for delay in [100, 500, 100]:
            for i in range(0, 3):
                led.on()
                time.sleep_ms(delay)
                led.off()
                time.sleep_ms(100)
            time.sleep_ms(200)
        time.sleep_ms(750)

led.off()

input_buffer = memoryview(bytearray(22500))
data_buffer = memoryview(bytearray(16875))

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
def base64_decode_single(four_in, three_out):
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
        bytes_decoded += base64_decode_single(input_buf[4 * i : 4 * (i + 1)], output_buf[bytes_decoded : bytes_decoded + 3])
    return bytes_decoded

mem_info()
last_successful_post = None

while True:
    try:
        cl, addr = s.accept()
        mem_info()
        print('Client connected from', addr)
        addr = None
        request = cl.recv(2048)
        # avoid memory issues by not decoding to ascii
        if len(request) > 0 and request[0] == 80: #'P' for post
            print(request)
            if request[6] == 107 and request[7] == 105 and request[8] == 108 and request[9] == 108: # "POST /kill"
                cl.send(f"""HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
                        <html>
                            <body style='font-family: "system-ui", serif;text-align:center'>
                                SHUTTING DOWN.
                            </body>
                        </html>""")
                cl.close()
                cl = None
                request = None
                break
            
            block_number = request[11] - 48
            if (block_number < 0 or block_number >= epd.expected_block_count):
                cl.send("HTTP/1.0 404 Bad block_number " + block_number)
                cl.close()
                cl = None
                request = None
                continue
            
            start = 0
            for i in range(len(request) - 3):
                if(request[i] == 13 and request[i + 1] == 10 and request[i + 2] == 13 and request[i + 3] == 10):
                    # found frame start
                    start = i + 4
                    break
            if (i == 0):
                cl.send("HTTP/1.0 400 Bad Request (no start found)\r\n")
                cl.close()
                cl = None
                request = None
                continue

            request = None
            gc.collect()
            buffer_index = 0
            chunk_length = 0

            print('Reading buffer')
            while True:
                try:
                    chunk_length = cl.readinto(input_buffer[buffer_index: buffer_index + 1], 1)
                except Exception as e:
                    if e.errno != 110:
                        print('memorybuffer readinto exception')
                        print(e)
                    break
                buffer_index += chunk_length
                if chunk_length == 0:
                    break

            gc.collect()
            print("Buffer length", buffer_index)

            # This will crash: data = bytes(binascii.a2b_base64(bytes(buffer[0: buffer_index]).decode('ascii')))
            bytes_decoded = base64_decode(input_buffer, data_buffer, buffer_index)
            data = data_buffer[0: bytes_decoded]

            if (len(data) == 0):
                cl.send("HTTP/1.0 400 Bad Request\r\n")
                cl.close()
                cl = None
                continue
            
            def send_response(status_code, status_text):
                cl.send(f'HTTP/1.0 {status_code} {status_text}\r\n')
                cl.close()
                if status_code == 200:
                    if block_number + 1 == epd.expected_block_count:
                        print('Successfully finished last POST')
                        # Successfully finished last POST
                        last_successful_post = None
                    else:
                        last_successful_post = time.time()
            try:
                led.on()
                epd.process_data_block(data, block_number, send_response)
                led.off()
            except Exception as e:
                print(e)
                send_response(500, 'Server error\r\n')
            data = None
            cl = None
            request = None
            gc.collect()
            continue

        if len(request) > 0 and request[0] == 71: # 'G' for GET
            requestStr = request.decode('utf-8')
            requestLines = requestStr.split()
            uri = requestLines[1]
            if uri.endswith('/'):
                uri += 'index.html'
            try:
                extension = uri[uri.find('.'):]
                mimetype = ''
                if extension == '.html':
                    mimetype = 'text/html'
                if extension == '.js':
                    mimetype = 'text/javascript'
                if extension == '.css':
                    mimetype = 'text/css'
                if extension == '.txt':
                    mimetype = 'text/plain'
                extension = None
                content = ''
                print(f'GET {uri}')
                if mimetype != '':
                    try:
                        with open(f'{uri}', 'r') as requestedFile:
                            content = requestedFile.read()
                        if len(content) > 0:
                            cl.send(f'HTTP/1.0 200 OK\r\nContent-type: {mimetype}\r\n\r\n')
                            index = 0
                            while index < len(content):
                                # print(content[index:index + 800])
                                index += cl.send(content[index:index + 800])
                            print('Successfully loaded content', uri)
                            content = None
                        else:
                            cl.send('HTTP/1.0 400 Bad Request\r\n')
                    except Exception as e:
                        print(e)
                        cl.send('HTTP/1.0 404 Not Found\r\n')
                else:
                    cl.send('HTTP/1.0 403 Forbidden\r\n')
                cl.close()

            except Exception as e:
                print(e)
                cl.send('HTTP/1.0 404 Not Found\r\n')
                cl.close()
            finally:
                requestStr = None
                requestLines = None
                request = None
                uri = None
                cl = None
                gc.collect()

        
    except OSError as e:
        if e.errno != 110:
            print(e)
        else:
            # Timeout error, should be once per second when device is idle
            if (last_successful_post is not None) and (time.time() - last_successful_post > 3600):
                # This happens when we've been waiting for a POST request for an hour.
                # Reset POST sequence state variables
                block_number = 0
                last_successful_post = None
                print(f'Last successful POST request was {time.time() - last_successful_post} seconds ago, putting display to sleep.')
                led.on()
                epd.reset()
                epd.delay_ms(2000)
                epd.sleep()
                led.off()
            else:
                # Check button
                if button_0_flag:
                    # Reset POST sequence state variables
                    block_number = 0
                    last_successful_post = None
                    # Turn on the LED
                    led.on()
                    ip = None
                    if wlan.isconnected():
                        ifconfig = wlan.ifconfig()
                        ip = str(ifconfig[0])
                        display_lines('HTTP address:', ip) # displayLines() takes care of putting display to sleep
                    else:
                        display_lines('NOT CONNECTED.')
                    button_flag_0 = False
                    led.off()
                elif button_1_flag:
                    button_1_flag = False
                    break
print('Exiting.')