from micropython import mem_info
from machine import Pin
import os
import network
import socket
import time
import urequests
import time
import gc
import binascii
import re
import random
import framebuf # For displaying status text messages

import rp2 # RP-2040

from epd import EPD_2in9_B, EPD_3in7, EPD_5in65, EPD_7in5_B

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
except:
    print('Could not find/parse device.txt.')

print('device', device)
print('country', country)

rp2.country(country)

# General setup

# USER BUTTONS - These are completely optional.
button_0 = None # If set, will display IP address on display
button_1 = None # If set, will clear and reset display and put it in sleep mode
button_2 = None # If set, will call machine.reset()

if device == 'EPD_5in65':
    # The 5.65 inch display has three buttons mounted on the PCB.
    # These are connected via pull-up resistors to GPIO 15, GPIO 17, and GPIO 2.
    button_0 = Pin(15, Pin.IN, Pin.PULL_UP) # GPIO 15
    button_1 = Pin(17, Pin.IN, Pin.PULL_UP) # GPIO 17
    button_2 = Pin(2, Pin.IN, Pin.PULL_UP)  # GPIO 2
elif device == 'EPD_7in5_B':
    # The 7.5 inch display has three buttons connected via pull-up resistors to GPIO 2, GPIO 3, and the RUN pin.
    button_0 = Pin(2, Pin.IN, Pin.PULL_UP) # GPIO 2
    button_1 = Pin(3, Pin.IN, Pin.PULL_UP) # GPIO 3
# The 4.2 inch display has two buttons connected via pull-up resistors to GPIO 15 and GPIO 17.

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
    raise SystemExit

# These flags will be checked after every socket timeout while we're waiting for a connection
button_flag_0 = False
button_flag_1 = False
button_flag_2 = False

def callback(pin):
    global button_flag_0, button_flag_1, button_flag_2
    if pin == button_0:
        button_flag_0 = True
    if pin == button_1:
        button_flag_1 = True
    if pin == button_2:
        button_flag_2 = True

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

# This method handles all the details for getting a wireless connection even if we
# don't know the SSID / password and have to display messages to the user
def get_wi_fi_connection(displayLines):

    # First check for a stored wireless configuration file  
    ssid = ''
    psk = ''
    wlan = None
    try:
        with open('./wi-fi.conf', 'r') as wpa:
            lines = wpa.read()
            ssid_match = re.search("ssid\s*=\s*\"?(\w+)\"?", lines)
            if ssid_match is not None:
                ssid = ssid_match.group(1)
            psk_match = re.search("psk\s*=\s*\"?(\w+)\"?", lines)
            if psk_match:
                psk = psk_match.group(1)

    except OSError: # open failed
        print('No wi-fi.conf file.')

    if (ssid == '' or psk == ''):
        print('No SSID credentials found stored in Flash.')
    else:
        print("Network SSID", ssid)

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, psk)

        while not wlan.isconnected() and wlan.status() >= 0:
            print("Waiting to connect to network", ssid)
            time.sleep(1.0)
        if wlan.isconnected():
            ifconfig = wlan.ifconfig()
            print('Connected, status', wlan.status())
            print('status', wlan.status())
            print('wlan', wlan)

            ifconfig = wlan.ifconfig()
            print('ifconfig', ifconfig)

            addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

            s = socket.socket()
            s.settimeout(1) # 1 second
            try:
                s.bind(addr)
            except Exception as e:
                print('Error binding socket.')
                print(e)
                if (e.errno == 98):
                    displayLines('ADDRESS IN USE', 'Needs restart.')
                    raise SystemExit
            s.listen(1)
            
            ip = str(ifconfig[0])
            # If this is a new IP, display it to the user
            novel_ip = True
            try:
                with open('./last-ip.txt', 'r') as ipfile:
                    if ipfile.read() == ip:
                        novel_ip = False
            except:
                pass
            
            if novel_ip:
                try:
                    with open('./last-ip.txt', 'w') as ipfile:
                        ipfile.write(ip)
                except:
                    pass
                displayLines('MY IP:', str(ifconfig[0]))
            
            return s # Success, return socket
        else:
            print('Connection failed, status', wlan.status())
            wlan.active(False)
            wlan.deinit()
    # Well crap...    
    # INITIAL SETUP MODE- OPEN A WIRELESS ACCESS POINT like we're setting up a new TV
    ap = network.WLAN(network.AP_IF)

    ap_ssid = 'epaper-' + str(random.randint(100,999))
    ap_psk = 'inky-' + str(random.randint(100, 999))

    ap.config(essid=ap_ssid, password=ap_psk)
    ap.active(True)
    
    while not ap.active:
        pass
    
    ifconfig = ap.ifconfig()
    print(f'Network SSID: {ap_ssid}  Password: {ap_psk}  URL: http://{ifconfig[0]}')
    displayLines('Network SSID:', ap_ssid, '', 'Password:', ap_psk, '', 'Local IP:', str(ifconfig[0]))

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(120)
    s.bind(addr)
    s.listen(1)
    while True:
        try:
            cl, addr = s.accept()
            try:
                print('Client connected from', addr)
                request = cl.recv(2048)
                request_text = request.decode('ascii')
                print(request_text)
                if request_text.startswith("POST /wifi"):
                    ssid_match = re.search("ssid=(\w+)", request_text)
                    if ssid_match is not None:
                        ssid = ssid_match.group(1)
                    psk_match = re.search("psk=(\w+)", request_text)
                    if psk_match is not None:
                        psk = psk_match.group(1)
                    print('ssid', ssid)
                    print('psk', psk)
                    with open('./wi-fi.conf', 'w') as conf_file:
                        conf_file.write(f'ssid="{ssid}"\npsk="{psk}"')
                    cl.send(f"""HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
                        <html>
                            <body style='font-family: "system-ui", serif;text-align:center'>
                                SUCCESS. Power cycle the device to have it connect to {ssid}.
                            </body>
                        </html>""")
                    cl.close()
                    s.close()
                    raise SystemExit
                    break
                
                if request_text.startswith('GET '):
                    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    content = f"""
                        <html>
                            <body style='font-family: "system-ui", serif;text-align:center'>
                                <h1>E-Paper Frame</h1>
                                <h2>WIRELESS NETWORK SETUP</h2>
                                <form action="/wifi" method="POST">
                                  <label for="ssid">Network SSID:</label><br>
                                  <input type="text" id="ssid" name="ssid" value="{ssid}"><br>
                                  <label for="psk">Password:</label><br>
                                  <input type="password" id="psk" name="psk" value="{psk}"><br><br>
                                  <input type="submit" value="Submit">
                                </form>
                            </body>
                        </html>
                    """
                    index = 0
                    while index < len(content):
                        # print(content[index:index + 800])
                        index += cl.send(content[index:index + 800])
                    cl.close()
            except Exception as e:
                if e.errno != 110:
                    print('Error handling request')
                    print(e)
                cl.send(f"HTTP/1.0 500 Server error (errno {e.errno})\r\n")
                cl.close()
                continue
        except Exception as e:
            if e.errno != 110:
                print('Error listening on socket')
                print(e)
            continue
    return wlan

epd = None
if device == 'EPD_2in9_B':
    epd = EPD_2in9_B()
elif device == 'EPD_3in7':
    epd = EPD_3in7()
elif device == 'EPD_5in65':
    epd = EPD_5in65()
elif device == 'EPD_7in5_B':
    epd = EPD_7in5_B()

def displayLines(*args):
    epd.displayMessage(*args)
    epd.delay_ms(2000)
    epd.sleep()

led.on()
s = get_wi_fi_connection(displayLines)
led.off()

mem_info()

incoming_buffer = bytearray(24576)

last_successful_post = None

while True:
    try:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(2048)
        
        if len(request) > 0 and request[0] == 80: #'P' for post
            print(request)
            block_number = request[11] - 48
            if (block_number < 0 or block_number >= epd.expected_block_count):
                cl.send("HTTP/1.0 404 Bad block_number " + block_number)
                cl.close()
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
                continue

            buffer = memoryview(incoming_buffer)
            buffer_index = 0
            chunk_length = 0

            print('Reading buffer')
            while True:
                try:
                    chunk_length = cl.readinto(buffer[buffer_index: buffer_index + 1], 1)
                except Exception as e:
                    if e.errno != 110:
                        print('memorybuffer readinto exception')
                        print(e)
                    break
                buffer_index += chunk_length
                if chunk_length == 0:
                    break

            gc.collect()
            print("Buffer length", len(buffer[0: buffer_index]))
            try:
                params = bytes(buffer[0: buffer_index]).decode('ascii')
            except Exception as e:
                print(e)
                cl.send("HTTP/1.0 500 Server error\r\n")
                cl.close()
                continue
            try:
                data = bytes(binascii.a2b_base64(params))
            except Exception as e:
                print('Throwing 500 error for exception', e)
                cl.send("HTTP/1.0 500 Incorrect padding\r\n")
                cl.close()
                continue
            params = None
            print('Deta length', len(data))
            gc.collect()
            
            if (len(data) == 0):
                cl.send("HTTP/1.0 400 Bad Request\r\n")
                cl.close()
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
            gc.collect()
            mem_info()

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
                # Check buttons
                if button_flag_0 or button_flag_1 or button_flag_2:
                    # Reset POST sequence state variables
                    block_number = 0
                    last_successful_post = None
                    # Turn on the LED
                    led.on()
                    if button_flag_0:
                        print("Detected button 0")
                        ip = 'UNKNOWN'
                        try:
                            with open('./last-ip.txt', 'r') as ipfile: # TODO - get this from the socket instead (WLAN not in scope)
                                ip = ipfile.read()
                        except:
                            pass                    
                        displayLines('MY IP:', ip) # displayLines() takes care of putting display to sleep
                        button_flag_0 = False
                    elif button_flag_1:
                        print("Detected button 1")
                        epd.init()
                        print('Clearing')
                        epd.clear()
                        print('Delay')
                        epd.delay_ms(2000)
                        print('sleep...')
                        epd.sleep()
                        print('done.')
                        button_flag_1 = False
                    elif button_flag_2:
                        print("Detected button 2")
                        epd.reset()
                        epd.delay_ms(2000)
                        epd.sleep()
                        button_flag_2 = False
                    # Finished interacting with display, turn LED off
                    led.off()
