from micropython import mem_info
import machine
import network
import socket
import time
import urequests
import time
import rp2
import gc
import binascii
import re
from epd import EPD_2in9_B, EPD_3in7, EPD_5in65

rp2.country("US")

ssid = ''
psk = ''

# Looks in a file wpa_supplicant.conf for two lines of the form
#
#        ssid="My_Network_SSID"
#        psk="Password123"
#
try:
    with open('./wpa_supplicant.conf', 'r') as wpa:
        lines = wpa.read()
        ssid_match = re.search("ssid\s*=\s*\"(\w+)\"", lines)
        if ssid_match is not None:
            ssid = ssid_match.group(1)
        psk_match = re.search("psk\s*=\s*\"(\w+)\"", lines)
        if psk_match:
            psk = psk_match.group(1)
        
except OSError: # open failed
    print('No wpa_supplicant.conf file.')

if (ssid == '' or psk == ''):
    print('No SSID credentials.')
    raise SystemExit

print("Network SSID", ssid)

with open('./device.txt', 'r') as device_txt:
    device_lines = device_txt.read()
    for line in device_lines.split("\n"):
        stripped = line.strip()
        if len(stripped) > 0 and stripped.startswith("#") is False:
            comment_pos = stripped.find("#")
            nocomment = stripped if comment_pos == -1 else stripped[0: comment_pos].strip()
            if len(nocomment) > 0:
                device = nocomment
                break

print('device', device)

led = machine.Pin("LED", machine.Pin.OUT)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, psk)

while not wlan.isconnected() and wlan.status() >= 0:
    print("Waiting to connect.")
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
led.off()
ifconfig = wlan.ifconfig()

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.settimeout(1) # 1 second
s.bind(addr)
s.listen(1)

print(f'Listening on {ifconfig[0]}')
mem_info()

epd = None
if device == 'EPD_2in9_B':
    epd = EPD_2in9_B()
if device == 'EPD_3in7':
    epd = EPD_3in7()
if device == 'EPD_5in65':
    epd = EPD_5in65()

incoming_buffer = bytearray(24576)

while True:
    try:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(2048)
        
        if len(request) > 0 and request[0] == 80: #'P' for post
            print('POST')
            print(request)
            print('length', len(request))
            block_number = request[11] - 48
            print('block number', str(block_number))
            if (block_number < 0 or block_number > 9):
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

            while True:
                try:
                    chunk_length = cl.readinto(buffer[buffer_index: buffer_index + 1], 1)
                except Exception as e:
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
            except:
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
            try:
                epd.process_data_block(data, block_number, send_response)
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
                    except:
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
