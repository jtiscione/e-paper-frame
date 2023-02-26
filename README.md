# E-Paper Frame

#### Remotely control an e-ink display with a Raspberry Pi Pico W.

This project runs a little HTTP server on your local network, using a Pico W connected to an e-paper display.
It serves up a crude MS Paint clone written in JavaScript, designed for e-ink.

You can paste an image, scale and place it, and perform Floyd Steinberg dithering on the result, restricting pixels to
colors supported by the display. There are also tools for scribbling, drawing boxes, and adding text.

Once you click the upload button to render the image on the display, the app will send the encoded image data to the
Pico W using a series of HTTP POST requests. The image will then remain displayed even if power is disconnected.

# SUPPORTED DEVICES

So far six Waveshare boards are supported:
- 2.13 inch two color display
- 2.9 inch two color display
- 3.7 inch four color grayscale display
- 4.2 inch four color grayscale display
- 5.65 inch 7 color ACeP display
- 7.5 inch two color display

The script assigns a code to each type of display.

### EPD_2in13B

2.13 inch 104x212 red/black e-ink display.
UI allows use of white, red, and black only.
Since this is a narrow and tall display (104 x 212 pixels), the UI positions it sideways by default.

### EPD_2in9B

2.9 inch 128x296 red/black e-ink display:
![2.9 inch red/black](https://user-images.githubusercontent.com/5413726/209608688-c21e2d4e-a2aa-4d39-a567-ea5c9bbd1d2c.png)
UI allows use of white, red, and black only.
![2.9 inch red/black UI](https://user-images.githubusercontent.com/5413726/209608755-eeca634d-5a3b-45a0-868a-5f21c0d65bf9.png)
Since this is a narrow and tall display (128 x 296 pixels), the UI positions it sideways by default.

### EPD_3in7

3.7 inch 280x480 four-color grayscale e-ink display:
![3.7 inch 4-color grayscale](https://user-images.githubusercontent.com/5413726/209608637-6d25bd56-b9b4-47fc-9109-2b22800c018b.png)
UI allows use of black, white, light gray, and dark gray.
![3.7 inch 4-color grayscale UI](https://user-images.githubusercontent.com/5413726/209608665-6353bade-e588-4d14-8b14-b4f0e2c77561.png)
Since this is a narrow and tall display (280 x 480 pixels), the UI positions it sideways by default.

### EPD_4in2
4.2 inch 400x300 four-color grayscal e-ink display.
UI allows use of white, red, and black only.

### EPD_5in65

5.65 inch 7-color ACeP display: This display has a resolution of 600 x 448 pixels.
![5.65-inch Van Gogh](https://user-images.githubusercontent.com/5413726/209608364-7d4c11ec-20b8-4f9b-a6ed-3362518f4197.png)

(The frame above is 3D printable; model files are in the `stl`folder. It is designed to fit the Pico e-Paper module.)

The UI allows use of 7 colors (as well as a blank color with no ink)
![5.65-inch Van Gogh UI](https://user-images.githubusercontent.com/5413726/209608489-0be822aa-fd57-49d8-bf23-fdae95ebe289.png)

### EPD_7in5_B
7.5 inch red/black e-ink display, resolution 800 x 480. I don't physically have one of these so I don't know if it works.

# WIRING

All of these e-paper devices are assumed to be wired as follows:

- RST PIN: GPIO 12
- DC PIN: GPIO 8
- CS PIN: GPIO 9
- BUSY PIN: GPIO 13

The 5.65 inch display also has three buttons on it connected with PULL_UP resistors. The script listens for these.
All three buttons will clear any upload sequence in progress.

- GPIO 15: Displays the current IP address on the e-paper display. If this button is being pressed on startup, it will erase the stored wireless configuration file and enter its network setup mode.
- GPIO 17: Clears the screen, resets the display, and puts it to sleep.
- GPIO 2: Resets the display and puts it to sleep.

# SETUP
The following files must be transferred to the Pico W filesystem using Thonny or rshell:

- `index.html`
- `index.css`
- `index.js`
- `device.txt` (specifying a country code and one of the device codes above)
- `main.py`
- The `lib` folder (including `base64_decoder.py`, `bootstrap_wifi.py`, `epd.py`, etc.)

Unfortunately there is no way for the Pico to automatically determine which type of e-paper device it is connected to.
There is also, obviously, no way to automatically figure out the country code to use for the wireless configuration.
So the Pico W filesystem must contain a file named `device.txt` that contains two lines of the form:

```
device="EPD_5in65"
country="US"
```

If you do not have a 5.65 inch display, you need to edit device.txt and replace its device "EPD_5in65" with one of the
other currently supported codes (currently "EPD_3in7" and "EPD_2in9B" are supported). You must also edit `device.txt`
with the correct code if you do not live in the U.S. so that the wi-fi works correctly.

After transferring these six files to the Pico, it can be disconnected. The `main.py` script will start up once the Pico
is connected to USB power.

Since there are no wi-fi credentials set up initially, the e-paper display will render a message within a minute,
reporting that it has created its own wireless access point. It will display the network name and password,
along with its IP address. (This will also happen if your wi-fi setup is changed in the future and it can't connect.)

Connecting to the network and loading the address in a browser will display a form where you can enter your
wireless SSID and password. After submitting the form, a message is displayed telling you to power cycle the device.

If you'd rather skip this procedure, you can add a `wi-fi.conf` file to the Pico using Thonny or rshell, to specify
the wireless SSID / password. It needs to contain two lines of the form:

```
ssid="My-Wireless-Network"
psk="password123"
```

Upon restart, the LED on the Pico will blink a while, and then go out once it connects successfully.
The screen will then display a message reporting the IP address on your wi-fi network. This message will not reappear
unless it acquires a different IP later on, or the user closes a switch connected to GPIO 15 with a pull-up resistor.
(This is the topmost button on the 5.65 inch display.)

The Pico usually shows up on the local wireless network as a device named `PYBD`.

# IMPLEMENTATION NOTES

Waveshare's documentation is limited; their sample code typically abstracts away the device into an object that uses a
large MicroPython FrameBuffer causing memory problems.

To avoid memory problems on the Pico, I avoided using FrameBuffer; most image processing is being done on the client
using JavaScript, which has much more memory and resources available.

The JavaScript code performs dithering of the image to restrict each pixel to one of several allowable colors.
When uploading, the image data is processed into a form compatible with the MicroPython FrameBuffer data format
expected by the device. It is subsequently base64 encoded to be sent in a series of HTTP POST requests.

As the Pico receives each POST request, it base64 decodes the data and streams it to the SPI channel (along
with any necessary device commands, etc.) before responding to the request with 200 OK. The client will only then
proceed with the next request. The protocol surrounding this process varies slightly according to the device, since they
all accept data in different FrameBuffer formats such as FrameBuffer.HLSB and FrameBuffer.HMSB, and the procedure is a
little different from one to the next:

- `EPD_2in13B`: receives 2 POST requests, one with HLSB data for black and one with HLSB data for red.
- `EPD_2in9B`: receives 2 POST requests, one with HLSB data for black and one with HLSB data for red.
- `EPD_3in7`: receives 2 POST requests, one with HLSB data for black and dark gray vs white and light gray, and one with HLSB data for black and light gray vs white and dark gray. (Both are sent to the device sequentially for a 4 color result.)
- `EPD_4in2`: receives 2 POST requests, one with HLSB data for black and dark gray vs white and light gray, and one with HLSB data for black and light gray vs white and dark gray. (Both are sent to the device sequentially for a 4 color result.)
- `EPD_5in65`: receives 8 POST requests. They contain data for one large HMSB buffer split into 8 horizontal bands (due to memory constraints).
- `EPD_7in5B`: receives 8 POST requests. Each HLSB buffer is split into 4 horizontal bands (due to memory constraints), four with data for black and four with data for red.

POST endpoints are of the form `/block0`, `/block1`, etc. and the sequence is expected by the server.
Requests received in an unexpected order result in an HTTP 409 error sent to the client, which will retry up to several
times starting with `/block0`.

Once the required amount of POST requests have been processed and streamed to the SPI channel, the Pico commands the e-ink display to show the image.

# TODO

These are codes to be used for various WaveShare displays (named after their example scripts).
So far this project only supports e-ink devices I actually have. There is code for EPD-7in5B but I haven't tried running it, so it probably has a typo.

- [ ] EPD_2in13: 2.13 inch display
- [x] EPD_2in13B: the red/black version
- [ ] EPD_2in66: 2.66 inch display
- [ ] EPD_2in66B: the red/black version
- [ ] EPD_2in9: 2 color 2.9 inch 4-color grayscale display
- [x] EPD_2in9B: the red/black version
- [x] EPD_3in7: 3.7 inch 4-color grayscale display
- [x] EPD_4in2: 4.2 inch 4-color grayscale display
- [ ] EPD_4in2B: the red/black version
- [x] EPD_5in65: 7-color ACeP display
- [ ] EPD_5in83: 5.83 inch 4-color grayscale display
- [ ] EPD_5in83B: the red/black version
- [ ] EPD_7in5 is the 7.5 inch 4-color grayscale display
- [x] EPD_7in5B is the red/black version (UNTESTED)

Will check these off as support gets added.

Additional TODOs:

- [ ] Fix all bugs with tools in the toolbar
- [ ] Support touch events on mobile devices
- [ ] Improve Floyd-Steinberg palette color selection
