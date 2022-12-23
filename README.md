# E-Paper Frame

#### Remotely control an e-ink display with a Raspberry Pi Pico W.

This project will run a little HTTP server on your local network.
It serves up a crude MS Paint clone written in JavaScript, written specifically
for an e-ink display.

You can paste an image, scale and place it, and perform Floyd Steinberg
dithering on the result. There are also tools for scribbling, drawing boxes,
and adding text.

When you are ready you can render the image on the display, the app will
format the image data into one HLSB buffer per color (excluding white)
and send the data base-64 encoded to the Pico W via HTTP POST.

The Pico W needs a file device.txt containing one of the following strings:

EPD_2in9_B       (for the 2.9 inch red/black/white display)
EPD_3in7         (for the 3.7 inch black / dark gray / light gray / white display)
EPD_5in65        (for the 5.65 inch 7 color aCEP dsplay)
