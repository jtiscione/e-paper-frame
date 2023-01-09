from machine import Pin, SPI
import framebuf
import gc
import utime

from epd import EPD

class EPD_7in5_B(EPD):

    def __init__(self):
        super().__init__(800, 480)
        self.expected_block_count = 4 # Two blocks for red, two blocks for black

    def WaitUntilIdle(self):
        print("e-Paper busy")
        while(self.digital_read(self.busy_pin) == 0):   # Wait until the busy_pin goes LOW
            self.delay_ms(20)
        self.delay_ms(20)
        print("e-Paper busy release")

    def TurnOnDisplay(self):
        self.send_command(0x12) # DISPLAY REFRESH
        self.delay_ms(100)      #!!!The delay here is necessary, 200uS at least!!!
        self.WaitUntilIdle()

    def init(self, *args):
        # EPD hardware init start
        self.reset()

        self.send_command(0x06)     # btst
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x28)        # If an exception is displayed, try using 0x38
        self.send_data(0x17)

#         self.send_command(0x01)  # POWER SETTING
#         self.send_data(0x07)
#         self.send_data(0x07)     # VGH=20V,VGL=-20V
#         self.send_data(0x3f)     # VDH=15V
#         self.send_data(0x3f)     # VDL=-15V

        self.send_command(0x04)  # POWER ON
        self.delay_ms(100)
        self.WaitUntilIdle()

        self.send_command(0X00)   # PANNEL SETTING
        self.send_data(0x0F)      # KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f

        self.send_command(0x61)     # tres
        self.send_data(0x03)     # source 800
        self.send_data(0x20)
        self.send_data(0x01)     # gate 480
        self.send_data(0xE0)

        self.send_command(0X15)
        self.send_data(0x00)

        self.send_command(0X50)     # VCOM AND DATA INTERVAL SETTING
        self.send_data(0x11)
        self.send_data(0x07)

        self.send_command(0X60)     # TCON SETTING
        self.send_data(0x22)

        self.send_command(0x65)     # Resolution setting
        self.send_data(0x00)
        self.send_data(0x00)     # 800*480
        self.send_data(0x00)
        self.send_data(0x00)

        return 0

    def clear(self):

        # Clear black
        blanks = bytearray([0xff for e in range(0, self.width // 8)])
        self.send_command(0x10)
        for j in range(0, self.height):
            self.send_data_array(black_blacks)

        # Clear red (Clearing red means sending zeros)
        blanks = bytearray([0x00 for e in range(0, self.width // 8)])
        self.send_command(0x13)
        for j in range(0, self.height):
            self.send_data_array(red_blanks)

        blanks = None
        self.TurnOnDisplay()

    # Here for reference, not actually used
    def display(self, buffer_black, buffer_red):
        byes_width = int(self.width // 8)
        self.send_command(0x10)
        for j in range(0, self.height):
            self.send_data_array(buffer_black[j * bytes_width : (j + 1) * bytes_width])
        self.send_command(0x13)
        for j in range(0, self.height):
            self.send_data_array(buffer_red[j * bytes_width : (j + 1) * bytes_width])

        self.TurnOnDisplay()

    def displayMessage(self, *args):
        # Create a small framebuffer to display several lines of text in top left corner
        textBufferHeight = 12 * (1 + len(args))
        textBufferWidth = 300 # Just use left side of screen for this
        halfBufferWidth = textBufferWidth // 2
        textBufferByteArray = bytearray(textBufferHeight * halfBufferWidth)
        image = framebuf.FrameBuffer(textBufferByteArray, textBufferWidth, textBufferHeight, framebuf.GS4_HMSB)
        image.fill(0xff)
        for h in range(0, len(args)):
            image.text(str(args[h]), 5, 12 * (1 + h), 0x00)
        image = None

        self.init()
        self.send_command(0x10)
        # Top of black image
        partial_blanks = bytearray([0xff for e in range(0, (self.width - textBufferWidth) // 8)])
        for j in range(0, textBufferHeight):
            self.send_data_array(textBufferByteArray[j * (textBufferWidth // 8) : (j + 1) * (textBufferWidth // 8)])
            self.send_data_array(partial_blanks)

        blanks = bytearray([0xff for e in range(0, self.width // 8)])
        for j in range(textBufferHeight, self.height):
            self.send_data_array(blanks)

        # For some reason you clear the 7.5 inch display by filling black with 0xff and red with 0x00
        blanks = bytearray([0x00 for e in range(0, self.width // 8)])
        for j in range(0, self.height):
            self.send_data_array(blanks)

        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x02) # power off
        self.WaitUntilIdle()
        self.send_command(0x07) # deep sleep
        self.send_data(0xa5)

    def process_data_block(self, data, block_number, send_response):
        if (block_number == 0):
            self.init()
            self.send_command(0x10)
            self.send_data_array(data)
            send_response(200, 'OK')
            self.data_block_count = 1
        elif block_number != self.data_block_count:
            send_response(409, 'Conflict - expected block number ' + str(self.data_block_count))
            self.data_block_count = 0
        elif block_number == 1 or block_number == 2 or block_number == 3:
            self.send_data_array(data)
            send_response(200, 'OK')
            self.data_block_count = 1
        elif block_number == 4:
            # Usually displays interpret HLSB data using 0 for "on" and 1 for "off", so to clear you fill with 0xff.
            # Client always assumes HLSB display is inverted and flips the pixels on the client.
            # For some reason the red channel on this display is NOT inverted, so we have to flip it back.
            self.send_command(0x13)
            self.send_data_array([~e for e in data])
            send_response(200, 'OK')
            self.data_block_count += 1
        elif block_number == 5 or block_number == 6 or block_number == 7:
            self.send_data_array(data)
            send_response(200, 'OK')
            self.data_block_count = 1
        elif block_number == 8:
            self.send_data_array([~e for e in data])
            send_response(200, 'OK')
            self.data_block_count = 0
            self.TurnOnDisplay()
            self.delay_ms(2000)
            self.sleep()
