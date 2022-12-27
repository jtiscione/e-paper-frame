# E-Paper Frame

#### Remotely control an e-ink display with a Raspberry Pi Pico W.

This project will run a little HTTP server on your local network.
It serves up a crude MS Paint clone written in JavaScript, written specifically
for an e-ink display.

You can paste an image, scale and place it, and perform Floyd Steinberg
dithering on the result. There are also tools for scribbling, drawing boxes,
and adding text.

When you are ready you can render the image on the display, the app will send the
encoded image data to the Pico W using a series of HTTP POST requests.

# SUPPORTED DEVICES

So far three Waveshare boards are supported: the 2.9 inch two color display, the 3.7 inch
four color grayscale display, and the 5.65 inch 7 color ACeP display.

For the Pico to identify the e-ink device, the Pico W filesystem must contain a file named device.txt
containing one of the following device codes:

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

### EPD_5in65
5.65 inch 7-color ACeP display:
![5.65-inch Van Gogh](https://user-images.githubusercontent.com/5413726/209608364-7d4c11ec-20b8-4f9b-a6ed-3362518f4197.png)
UI allows use of 7 colors (as well as a blank color with no ink)
![5.65-inch Van Gogh UI](https://user-images.githubusercontent.com/5413726/209608489-0be822aa-fd57-49d8-bf23-fdae95ebe289.png)
This display has a resolution of 600 x 448 pixels.

# SETUP
The following files must be present in the Pico W filesystem:
- `index.html`
- `index.css`
- `index.js`
- `device.txt` (specifying one of the codes above)
- `main.py`
- `epd.py` (must be present in subfolder `lib`)
- `wpa_supplicant.conf`

The `wpa_supplicant.conf` file is needed to get the wireless configuration.
This file doesn't need to be a "real" `wpa_supplicant.conf` file, although one will work;
it just needs to contain two lines of the form:
```
ssid="My-Wireless-Network"
psk="Password123"
```

# TASKS

These are codes to be used for various WaveShare displays (named after their example scripts).
So far only three are supported.

- [ ] EPD_2in66: 2.66 inch display
- [ ] EPD_2in66B: the red/black version
- [ ] EPD_2in9: 2 color 2.9 inch 4-color grayscale display
- [x] EPD_2in9B: the red/black version
- [x] EPD_3in7: 3.7 inch 4-color grayscale display
- [ ] EPD_4in2: 4.2 inch 4-color grayscale display
- [ ] EPD_4in2B: the red/black version
- [x] EPD_5in65: 7-color ACeP display
- [ ] EPD_5in83: 5.83 inch 4-color grayscale display
- [ ] EPD_5in83B: the red/black version
- [ ] EPD_7in5 is the 7.5 inch 4-color grayscale display
- [ ] EPD_7in5B is the red/black version
