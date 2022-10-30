# Pico Inkwell

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

The Pico receives the base64 string for each color and streams them
directly to the SPI channel in the order that it expects to receive colors.

