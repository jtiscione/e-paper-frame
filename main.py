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

from base64_decoder import base64_decode

# We will have the LED on during startup while it's trying to connect to the network.
# If it cannot connect, the script enters "initial setup mode" and the LED remains on.
# Otherwise, the LED is only lit during interactions with the display.
led = Pin("LED", machine.Pin.OUT)

for i in range(0, 6):
    led.toggle()
    time.sleep_ms(150)
time.sleep_ms(500)

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
led.on()

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

led.off()

# Special function of button_0: if it's being pressed on startup, delete any cached connection info and quit.
if button_0 is not None and button_0.value() == 0:
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
    global button_0_flag, button_1_flag
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

led.on()

epd = None
if device == 'EPD_2in9_B':
    from EPD_2in9_B import EPD_2in9_B
    epd = EPD_2in9_B()
elif device == 'EPD_3in7':
    from EPD_3in7 import EPD_3in7
    epd = EPD_3in7()
elif device == 'EPD_5in65':
    from EPD_5in65 import EPD_5in65
    epd = EPD_5in65()
elif device == 'EPD_7in5_B':
    from EPD_7in5_B import EPD_7in5_B
    epd = EPD_7in5_B()

led.off()

def display_lines(*args):
    epd.displayMessage(*args)
    epd.sleep()

try:
    wlan, s = bootstrap_wifi(display_lines, led)
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
except Exception as e:
    print("Unexpected error:", e)
    sys.exit()

input_buffer = memoryview(bytearray(22500))
data_buffer = memoryview(bytearray(16875))

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
            print('Decoded base64')

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
                print('Processed data block.')
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
                    sent_header = False
                    try:
                        with open(f'{uri}', 'r') as requestedFile:
                            for line in requestedFile:
                                if sent_header is False:
                                    cl.send(f'HTTP/1.0 200 OK\r\nContent-type: {mimetype}\r\n\r\n')
                                    sent_header = True
                                cl.send(line)
                        if sent_header:
                            print('Sent content', uri)
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
            led.on()
            time.sleep_ms(1)
            led.off()
            
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
                    button_0_flag = False
                    led.off()
                elif button_1_flag:
                    button_1_flag = False
                    break
print('Exiting.')