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

# This method handles all the details for setting up a wireless connection.
# If we don't have the SSID / password yet, it will set up a wireless access point
# to serve an HTML form for entering the wifi credentials.
# 
# Argument display_lines is a function that takes a list of short strings and displays
# them to the user somehow.
# 
# The LAN stack on the Pico W remembers open sockets and open interfaces even through
# a soft reset. To bring that back to initial state, you have to perform a hard reset,
# either by taking the power off and on again, by pushing the reset button or pulling
# the reset line low. This is not comfortable, but unlikely to be changed.
# (Ref https://github.com/micropython/micropython/issues/3739)
#
# This function will specifically raise a RuntimeError if we get into a situation
# where the device needs to be restarted before we can continue, so a handler can
# do something like blink an LED indefinitely or invoke machine.reset().
#
# Returns the connection and a socket listening on port 80.
def bootstrap_wifi(display_lines, led, ssid_prefix, pwd_prefix):

    if led is None:
        led = Pin("LED", machine.Pin.OUT)
    if ssid_prefix is None:
        ssid_prefix = 'network-'
        pwd_prefix = 'pass-'


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
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        if wlan.isconnected():
            ifconfig = wlan.ifconfig()
            print('Connected, status', wlan.status())
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
                    # The dreaded EADDRINUSE error
                    try:
                        os.remove('./last-ip.txt')
                    except:
                        pass
                    display_lines('ADDRESS IN USE', 'Needs hard reset.')
                    raise RuntimeError('ADDRESS IN USE. Needs hard reset.')
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
                display_lines('HTTP address:', str(ifconfig[0]))
            return wlan, s # Success, return wlan and socket
        else:
            print('Connection failed, status', wlan.status())
            wlan.active(False)
            wlan.deinit()
    # Well crap...
    # INITIAL SETUP MODE- OPEN A WIRELESS ACCESS POINT like we're setting up a new TV
    ap = network.WLAN(network.AP_IF)

    ap_ssid = ssid_prefix + str(random.randint(100, 999))
    ap_psk = pwd_prefix + str(random.randint(100, 999))

    ap.config(essid=ap_ssid, password=ap_psk)
    ap.active(True)

    while not ap.active:
        pass

    ifconfig = ap.ifconfig()
    print(f'Network SSID: {ap_ssid}  Password: {ap_psk}  URL: http://{ifconfig[0]}')

    display_lines('Network SSID:', ap_ssid, 'Password:', ap_psk, 'HTTP address:', str(ifconfig[0]))


    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1) # 1 second
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
                    break
                
                if request_text.startswith('POST /kill'):
                    cl.send(f"""HTTP/1.0 200 OK\r\nContent-Type:text/html\r\n\r\n
                        <html>
                            <body style='font-family: "system-ui", serif;text-align:center'>
                                SHUTTING DOWN.
                            </body>
                        </html>""")
                    cl.close()
                    s.close()
                    sys.exit()
                
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
                                <hr>
                                <form action="/kill" method="POST">
                                    <div>To return to REPL: <input type="submit" value="EXIT SCRIPT"></div>
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
                time.sleep_ms(1000)
            led.on()
            time.sleep_ms(1)
            led.off()
            continue
    raise RuntimeError('SETTINGS CHANGED. Needs hard reset.')