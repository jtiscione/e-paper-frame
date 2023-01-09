from machine import Pin, SPI
import framebuf
import gc
import utime

from epd import EPD

class EPD_2in9_B(EPD):

    def __init__(self):
        super().__init__(128, 296)
        self.expected_block_count = 2

    def ReadBusy(self):
        print('busy')
        self.send_command(0x71)
        while(self.digital_read(self.busy_pin) == 0):
            self.send_command(0x71)
            self.delay_ms(10)
        print('busy release')

    def TurnOnDisplay(self):
        self.send_command(0x12)
        self.ReadBusy()

    def init(self, *args):
        self.reset()
        self.send_command(0x04)
        self.ReadBusy()#waiting for the electronic paper IC to release the idle signal

        self.send_command(0x00)    #panel setting
        self.send_data(0x0f)   #LUT from OTP,128x296
        self.send_data(0x89)    #Temperature sensor, boost and other related timing settings

        self.send_command(0x61)    #resolution setting
        self.send_data (0x80)
        self.send_data (0x01)
        self.send_data (0x28)

        self.send_command(0X50)    #VCOM AND DATA INTERVAL SETTING
        self.send_data(0x77)   #WBmode:VBDF 17|D7 VBDW 97 VBDB 57
                            # WBRmode:VBDF F7 VBDW 77 VBDB 37  VBDR B7
        return 0

    def clear(self):
        blanks = bytearray([0xff for e in range(0, self.width // 8)])

        # Clear black
        self.send_command(0x10)
        for j in range(0, self.height):
            self.send_data_array(blanks)

        # Clear red
        self.send_command(0x13)
        for j in range(0, self.height):
            self.send_data_array(blanks)
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

        self.init()
        # Create a small framebuffer to display several lines of text
        textBufferHeight = 12 * (1 + len(args))
        textBufferWidth = self.width # Buffer extends entire width
        textBufferByteArray = bytearray(textBufferHeight * textBufferWidth // 8)
        image = framebuf.FrameBuffer(textBufferByteArray, textBufferWidth, textBufferHeight, framebuf.MONO_HLSB)
        image.fill(0xff)
        for h in range(0, len(args)):
            image.text(str(args[h]), 5, 12 * (1 + h), 0x00)

        self.send_command(0x10)
        # Top of black image
        for j in range(0, textBufferHeight):
            self.send_data_array(textBufferByteArray[j * self.width // 8: (j + 1) * self.width // 8])
        image = None
        textBufferByteArray = None
        gc.collect()
        # Rest of black image
        blanks = bytearray([0xff for e in range(0, self.width // 8)])
        for j in range(textBufferHeight, self.height):
            self.send_data_array(blanks)
        self.send_command(0x13)
        # Red image is blank
        for j in range(0, self.height):
            self.send_data_array(blanks)
        blanks = None
        self.TurnOnDisplay()
        print('displayMessage() complete.')

    def sleep(self):
        self.send_command(0X02) # power off
        self.ReadBusy()
        self.send_command(0X07) # deep sleep
        self.send_data(0xA5)

        self.delay_ms(2000)
        self.module_exit()

    def process_data_block(self, data, block_number, send_response):
        bytes_width = int(self.width // 8)
        if (block_number == 0):
            self.init()
            # black buffer
            self.send_command(0x10)
            self.send_data_array(data)
            # for j in range(0, self.height):
            #   for i in range(0, bytes_width):
            #     self.send_data(data[i + j * bytes_width])
            send_response(200, 'OK')
            self.data_block_count = 1
        elif (block_number != self.data_block_count):
            send_response(409, 'Conflict - expected block number ' + str(self.data_block_count))
            self.data_block_count = 0
        elif (block_number == 1):
            # red buffer
            self.send_command(0x13)
            self.send_data_array(data)
            # for j in range(0, self.height):
            #   for i in range(0, int(self.width // 8)):
            #       self.send_data(data[i + j * int(self.width // 8)])
            send_response(200, 'OK')

            self.TurnOnDisplay()
            self.data_block_count = 0
            self.delay_ms(2000)
            self.sleep()
