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
from epd import EPD_2in9_B, EPD_3in7, EPD_5in65

def extract_urlencoded_param(params, paramName, asBytes=False, asNumber=False):
    startIndex = params.find(paramName+'=')
    endIndex = params.find('&', startIndex)
    if endIndex < 0:
        endIndex = len(params)
    if (asBytes):
        return bytearray(binascii.a2b_base64(params[startIndex + len(paramName) + 1 : endIndex]))
    val = params[startIndex + len(paramName) + 1 : endIndex]
    if (asNumber):
        return int(val)
    return val

rp2.country("US")

with open('./device.txt', 'r') as device_txt:
    device = device_txt.read()

print('device', device)

mem_info()

led = machine.Pin("LED", machine.Pin.OUT)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("Inversion_Lair", "789yuihjk")

while not wlan.isconnected() and wlan.status() >= 0:
    print("Waiting to connect.")
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
led.off()
print(wlan.ifconfig())

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.settimeout(1) # 1 second
s.bind(addr)
s.listen(1)

print(f'Listening on {addr}')
mem_info()

epd = None;
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
        # print(request)
        # print('length', len(request))
        
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

            print('start', start)

            buffer = memoryview(incoming_buffer)
            buffer_index = 0
            chunk_length = 0
            prev_chunk_length = 0

            while True:
                prev_chunk_length = chunk_length
                print("Receiving chunk...")
                try:
                    chunk_length = cl.readinto(buffer[buffer_index: buffer_index + 800], 800)
                except:
                    print('except')
                    break
                print("Received.")
                buffer_index += chunk_length
                print("buffer_index", buffer_index);
                if prev_chunk_length > chunk_length:
                    break
            print("Done loop...")
            gc.collect()
            print("Buffer length", len(buffer[0: buffer_index]))
            print("Decoding buffer")
            try:
                params = bytes(buffer[0: buffer_index]).decode('ascii')
            except:
                cl.send("HTTP/1.0 500 Server error\r\n")
                cl.close()
                continue
            # buffer = None
            print("Decoded.")
            gc.collect()
            print(params)
            print(len(params))
            try:
                data = bytes(binascii.a2b_base64(params))
            except:
                cl.send("HTTP/1.0 500 Incorrect padding\r\n")
                cl.close()
                continue
            params = None
            print(len(data))
            data = None
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
            except:
                send_response(500, 'Server error\r\n')
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
                if extension == '.json':
                    mimetype = 'application/json'
                if extension == '.txt':
                    mimetype = 'text/plain'
                content = ''
                print(f'GET {uri}')
                with open(f'{uri}', 'r') as requestedFile:
                    content = requestedFile.read()
                if len(content) > 0:
                    cl.send(f'HTTP/1.0 200 OK\r\nContent-type: {mimetype}\r\n\r\n')
                    index = 0
                    while index < len(content):
                        if (mimetype == 'text/javascript'):
                            print(content[index:index + 800])
                        cl.send(content[index:index + 800])
                        index += 800
                    print('Successfully loaded content', uri)
                else:
                    cl.send('HTTP/1.0 400 Bad Request\r\n')
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
