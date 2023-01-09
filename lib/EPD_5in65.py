from machine import Pin, SPI
import framebuf
import gc
import utime

from epd import EPD

class EPD_5in65(EPD):

    def __init__(self):
        super().__init__(600, 448)
        self.expected_block_count = 8
        self.Black = 0x00
        self.White = 0x01
        self.Green = 0x02
        self.Blue = 0x03
        self.Red = 0x04
        self.Yellow = 0x05
        self.Orange = 0x06
        self.Clean = 0x07

    def BusyHigh(self):
        while(self.digital_read(self.busy_pin) == 0):
            self.delay_ms(1)

    def BusyLow(self):
        while(self.digital_read(self.busy_pin) == 1):
            self.delay_ms(1)

    def init(self, *args):
        self.reset()
        self.BusyHigh()
        self.send_command(0x00)
        self.send_data(0xEF)
        self.send_data(0x08)
        self.send_command(0x01)
        self.send_data(0x37)
        self.send_data(0x00)
        self.send_data(0x23)
        self.send_data(0x23)
        self.send_command(0x03)
        self.send_data(0x00)
        self.send_command(0x06)
        self.send_data(0xC7)
        self.send_data(0xC7)
        self.send_data(0x1D)
        self.send_command(0x30)
        self.send_data(0x3C)
        self.send_command(0x41)
        self.send_data(0x00)
        self.send_command(0x50)
        self.send_data(0x37)
        self.send_command(0x60)
        self.send_data(0x22)
        self.send_command(0x61)
        self.send_data(0x02)
        self.send_data(0x58)
        self.send_data(0x01)
        self.send_data(0xC0)
        self.send_command(0xE3)
        self.send_data(0xAA)

        self.delay_ms(100)
        self.send_command(0x50)
        self.send_data(0x37)

    def clear(self):
        self.fill(self.Clean)

    def fill(self, color):

        self.send_command(0x61)   # Set Resolution setting
        self.send_data(0x02)
        self.send_data(0x58)
        self.send_data(0x01)
        self.send_data(0xC0)
        self.send_command(0x10)
        color2 = (color<<4)|color
        blanks = bytearray([color2 for e in range(0, int(self.width // 2))])
        for j in range(0, self.height):
            self.send_data_array(blanks)
        blanks = None
        self.send_command(0x04)   # 0x04
        self.BusyHigh()
        self.send_command(0x12)   # 0x12
        self.BusyHigh()
        self.send_command(0x02)   # 0x02
        self.BusyLow()
        self.delay_ms(500)

    # For reference, not used
    def display(self, data):

        self.send_command(0x61)   # Set Resolution setting
        self.send_data(0x02)
        self.send_data(0x58)
        self.send_data(0x01)
        self.send_data(0xC0)
        self.send_command(0x10)
        for i in range(0, self.height):
            for j in range(0, int(self.width // 2)):
                self.send_data(data[j + ((self.width // 2) * i)])

        self.send_command(0x04)   # 0x04
        self.BusyHigh()
        self.send_command(0x12)   # 0x12
        self.BusyHigh()
        self.send_command(0x02)   # 0x02
        self.BusyLow()
        self.delay_ms(200)

    def displayMessage(self, *args):
        print('In displayMessage()...')
        # Create a small framebuffer to display several lines of text in top left corner
        textBufferHeight = 12 * (1 + len(args))
        textBufferWidth = 300 # Just use left side of screen for this
        halfBufferWidth = textBufferWidth // 2
        textBufferByteArray = bytearray(textBufferHeight * halfBufferWidth)
        image = framebuf.FrameBuffer(textBufferByteArray, textBufferWidth, textBufferHeight, framebuf.GS4_HMSB)
        image.fill(0x77) # two "clean" pixels
        for h in range(0, len(args)):
            image.text(str(args[h]), 5, 12 * (1 + h), 0x00)  # two black pixels
        self.init()
        self.send_command(0x61)   # Set Resolution setting
        self.send_data(0x02)
        self.send_data(0x58)
        self.send_data(0x01)
        self.send_data(0xC0)
        self.send_command(0x10)
        print('Sending pixel data...')
        partial_blanks = bytearray([0x77 for e in range(0, int(self.width // 2 - halfBufferWidth))])
        for i in range(0, textBufferHeight): # self.height):
            row_byte_offset = i * halfBufferWidth
            self.send_data_array(textBufferByteArray[row_byte_offset : row_byte_offset + halfBufferWidth])
            self.send_data_array(partial_blanks)
        partial_blanks = None
        full_blanks = bytearray([0x77 for e in range(0, int(self.width // 2))])
        for i in range(textBufferHeight, self.height):
            self.send_data_array(full_blanks)
        full_blanks = None

        print('Finished sending pixel data.')
        self.send_command(0x04)   # 0x04
        self.BusyHigh()
        self.send_command(0x12)   # 0x12
        self.BusyHigh()
        self.send_command(0x02)   # 0x02
        self.BusyLow()
        print('Complete.')
        self.delay_ms(200)
        print('Returning from displayMessage().')

    def sleep(self):
        self.delay_ms(100)
        self.send_command(0x07)
        self.send_data(0xA5)
        self.delay_ms(100)
        self.digital_write(self.reset_pin, 1)

    # Will receive 8 POST requests, each with a block of 22400 base64 characters encoding 16800 bytes each.
    # Each block is a horizontal stripe of 56 rows of 448 pixels with each pixel occupying half a byte.
    def process_data_block(self, data, block_number, send_response):
        print(f'block_number {block_number}   self.data_block_count {self.data_block_count}')
        print('process_data_block() data length', len(data))
        if (block_number == 0):
            self.init()

            self.send_command(0x61)   # Set Resolution setting
            self.send_data(0x02)
            self.send_data(0x58)
            self.send_data(0x01)
            self.send_data(0xC0)
            self.send_command(0x10)
        else:
            if (block_number != self.data_block_count):
                send_response(409, 'Conflict - expected block number ' + str(self.data_block_count))
                self.data_block_count = 0
                return

        index = 0
        self.send_data_array(data)

        send_response(200, 'OK')

        self.data_block_count += 1

        if block_number == 7:
            self.send_command(0x04)   # 0x04
            self.BusyHigh()
            self.send_command(0x12)   # 0x12
            self.BusyHigh()
            self.send_command(0x02)   # 0x02
            self.BusyLow()
            self.delay_ms(200)

            self.data_block_count = 0
            self.delay_ms(2000)
            self.sleep()
