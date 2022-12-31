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
import random
import framebuf # For displaying status text messages
from epd import EPD_2in9_B, EPD_3in7, EPD_5in65

# This method handles all the details for getting a wireless connection even if we
# don't know the SSID / password and have to display messages to the user
def get_wi_fi_connection(displayLines):

    led = machine.Pin("LED", machine.Pin.OUT)
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
            led.off()
            time.sleep(0.5)
            led.on()
            time.sleep(0.5)
        if wlan.isconnected():
            led.off()
            ifconfig = wlan.ifconfig()
            print('Connected, status', wlan.status())
            print('status', wlan.status())
            print('wlan', wlan)

            ifconfig = wlan.ifconfig()
            print('ifconfig', ifconfig)

            addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

            s = socket.socket()
            s.settimeout(1) # 1 second
            s.bind(addr)
            s.listen(1)
            
            ip = str(ifconfig[0])
            # If this is a new IP, display it to the user
            novel_ip = True
            try:
                with open('last-ip.txt', 'r') as ipfile:
                    if ipfile.read() == ip:
                        novel_ip = False
            except:
                pass
            
            if novel_ip:
                try:
                    with open('last-ip.txt', 'w') as ipfile:
                        ipfile.write(ip)
                except:
                    pass
                displayLines('LOCAL IP:', str(ifconfig[0]))
            
            return s # Success, return socket
        else:
            print('Connection failed, status', wlan.status())
            wlan.active(False)
            wlan.deinit()
    # Well crap...
    
    # "BOOTSTRAP" MODE- OPEN A WIRELESS ACCESS POINT like we're setting up a new TV
    ap = network.WLAN(network.AP_IF)

    ap_ssid = 'epaper' + str(random.randint(100,999))
    ap_psk = 'inky' + str(random.randint(1000, 9999))

    ap.config(essid=ap_ssid, password=ap_psk)
    ap.active(True)
    
    while not ap.active:
        pass
    
    ifconfig = ap.ifconfig()
    # print('ifconfig', ifconfig)
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
                    cl.send(f"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>SUCCESS. Power cycle the device to have it connect to {ssid}.</body></html>")
                    cl.close()
                    s.close()
                    raise SystemExit
                    break
                if request_text.startswith("POST /skip"):
                    cl.send('HTTP/1.1 303 See Other\r\nLocation: /index.html')
                    cl.close()
                    return s
                
                if request_text.startswith('GET '):
                    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    content = f"""
                        <html>
                            <body style="text-align:center">
                                <h1>E-Paper Frame</h1>
                                <h2>WIRELESS NETWORK SETUP</h2>
                                <form action="/wifi" method="POST">
                                  <label for="ssid">Network SSID:</label><br>
                                  <input type="text" id="ssid" name="ssid" value="{ssid}"><br>
                                  <label for="psk">Password:</label><br>
                                  <input type="password" id="psk" name="psk" value="{psk}"><br><br>
                                  <input type="submit" value="Submit">
                                </form>
                                <hr/>
                                <h2>No wireless network? To skip this step and continue using this connection:</h2>
                                <form action="/skip" method="POST">
                                    <input type="submit" value="SKIP WI-FI SETUP"/>
                                </form>
                                <div><em>WARNING: The connection is extremely slow.</em></div>
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
                    print(e)
                cl.send(f"HTTP/1.0 500 Server error (errno {e.errno})\r\n")
                cl.close()
                continue
        except Exception as e:
            if e.errno != 110:
                print(e)
            continue
    return wlan


# Figure out what device we're using
device = 'EPD_5in65' # Let's assume we're using the 7 color display by default...
try:
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
except:
    print('Could not find/parse device.txt.')

print('device', device)

led = machine.Pin("LED", machine.Pin.OUT)

epd = None
if device == 'EPD_2in9_B':
    epd = EPD_2in9_B()
if device == 'EPD_3in7':
    epd = EPD_3in7()
if device == 'EPD_5in65':
    epd = EPD_5in65()


rp2.country("US")

def displayLines(*args):
    epd.init()
    # epd.clear()
    epd.displayMessage(*args)
    print('Returned from displayMessage')
    epd.delay_ms(2000)
    epd.sleep()
    print('Returned from sleep()')

s = get_wi_fi_connection(displayLines)

mem_info()

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

            print('Reading buffer')
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
