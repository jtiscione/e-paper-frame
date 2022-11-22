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
from epd import EPD_2in9_B

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
s.bind(addr)
s.listen(1)

print(f'Listening on {addr}')
mem_info()

epd = EPD_2in9_B()

while True:
    try:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(2048)
        # print(request)
        # print('length', len(request))
        
        if len(request) > 0 and request[0] == 80: #'P' for post
            print('POST')
            for i in range(len(request) - 3):
                if(request[i] == 13 and request[i + 1] == 10 and request[i + 2] == 13 and request[i + 3] == 10):
                    # found frame start
                    start = i + 4

                    buffer = bytearray(2048)
                    buffer_index = 0
                    chunk_length = 0
                    prev_chunk_length = 0

                    while True:
                        prev_chunk_length = chunk_length
                        chunk = cl.recv(2048)
                        chunk_length = len(chunk)
                        buffer[buffer_index: buffer_index + chunk_length] = chunk
                        buffer_index += chunk_length
                        if prev_chunk_length > chunk_length:
                            break
                    gc.collect()
                    params = buffer.decode('ascii')
                    buffer = None
                    gc.collect()

                    data = bytearray(binascii.a2b_base64(params))
                    params = None
                    gc.collect()
                    epd.process_data_block(data)
                    cl.send('HTTP/1.0 200 OK\r\n')
                    cl.close()
                    mem_info()
                    break

                    # black = extract_urlencoded_param(params, 'black', True, False)
                    # red = extract_urlencoded_param(params, 'red', True, False)
                    # params = None
                    # gc.collect()
                    # cl.send('HTTP 1.0 200 OK\r\n')
                    # cl.close()
                    # mem_info()

                    # epd = EPD_2in9_B()
                    # epd.set_buffers(black, red)
                    # epd.buffer_black = black
                    # epd.buffer_red = red
                    # epd.display()
                    # epd.delay_ms(2000)
                    # print("sleep")
                    # epd.sleep()
                    # gc.collect()
                    # mem_info()
                    # break
                            
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
        print(e)
