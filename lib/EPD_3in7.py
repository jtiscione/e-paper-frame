from machine import Pin, SPI
import framebuf
import gc
import utime

from epd import EPD

EPD_3IN7_lut_4Gray_GC = [
    0x2A,0x06,0x15,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#1
    0x28,0x06,0x14,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#2
    0x20,0x06,0x10,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#3
    0x14,0x06,0x28,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#4
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#5
    0x00,0x02,0x02,0x0A,0x00,0x00,0x00,0x08,0x08,0x02,#6
    0x00,0x02,0x02,0x0A,0x00,0x00,0x00,0x00,0x00,0x00,#7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#8
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#9
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#10
    0x22,0x22,0x22,0x22,0x22
]

EPD_3IN7_lut_1Gray_GC =[
    0x2A,0x05,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#1
    0x05,0x2A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#2
    0x2A,0x15,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#3
    0x05,0x0A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#4
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#5
    0x00,0x02,0x03,0x0A,0x00,0x02,0x06,0x0A,0x05,0x00,#6
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#8
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#9
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#10
    0x22,0x22,0x22,0x22,0x22
]

EPD_3IN7_lut_1Gray_DU =[
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#1
    0x01,0x2A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x0A,0x55,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#3
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#5
    0x00,0x00,0x05,0x05,0x00,0x05,0x03,0x05,0x05,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#9
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x22,0x22,0x22,0x22,0x22
]

EPD_3IN7_lut_1Gray_A2 =[
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#1
    0x0A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#2
    0x05,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#3
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#4
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#5
    0x00,0x00,0x03,0x05,0x00,0x00,0x00,0x00,0x00,0x00,#6
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#8
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#9
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,#10
    0x22,0x22,0x22,0x22,0x22
]

class EPD_3in7(EPD):

    def __init__(self):

        super().__init__(280, 480)
        self.expected_block_count = 2

        self.lut_4Gray_GC = EPD_3IN7_lut_4Gray_GC
        self.lut_1Gray_GC = EPD_3IN7_lut_1Gray_GC
        self.lut_1Gray_DU = EPD_3IN7_lut_1Gray_DU
        self.lut_1Gray_A2 = EPD_3IN7_lut_1Gray_A2

        self.black = 0x00
        self.white = 0xff
        self.darkgray = 0xaa
        self.grayish = 0x55

        # self.buffer_4Gray = bytearray(self.height * self.width // 4)
        # self.image4Gray = framebuf.FrameBuffer(self.buffer_4Gray, self.width, self.height, framebuf.GS2_HMSB)
        # self.clear()
        # utime.sleep_ms(500)

    def ReadBusy(self):
        print("e-Paper busy")
        while(self.digital_read(self.busy_pin) == 1):      #  0: idle, 1: busy
            self.delay_ms(10)
        self.delay_ms(200)
        print("e-Paper busy release")

    def Load_LUT(self,lut):
        self.send_command(0x32)
        for count in range(0, 105):
            if lut == 0 :
                self.send_data(self.lut_4Gray_GC[count])
            elif lut == 1 :
                self.send_data(self.lut_1Gray_GC[count])
            elif lut == 2 :
                self.send_data(self.lut_1Gray_DU[count])
            elif lut == 3 :
                self.send_data(self.lut_1Gray_A2[count])
            else:
                print("There is no such lut ")

    def init(self, *args):

        monochrome = False
        if len(args) > 0:
            monochrome = args[0]

        self.reset()              # SWRESET

        self.send_command(0x12)
        self.delay_ms(300)

        self.send_command(0x46)
        self.send_data(0xF7)
        self.ReadBusy()
        self.send_command(0x47)
        self.send_data(0xF7)
        self.ReadBusy()

        self.send_command(0x01)   # setting gaet number
        self.send_data(0xDF)
        self.send_data(0x01)
        self.send_data(0x00)

        self.send_command(0x03)   # set gate voltage
        self.send_data(0x00)

        self.send_command(0x04)   # set source voltage
        self.send_data(0x41)
        self.send_data(0xA8)
        self.send_data(0x32)

        self.send_command(0x11)   # set data entry sequence
        self.send_data(0x03)

        self.send_command(0x3C)   # set border
        self.send_data(0x03)

        self.send_command(0x0C)   # set booster strength
        self.send_data(0xAE)
        self.send_data(0xC7)
        self.send_data(0xC3)
        self.send_data(0xC0)
        self.send_data(0xC0)

        self.send_command(0x18)   # set internal sensor on
        self.send_data(0x80)

        self.send_command(0x2C)   # set vcom value
        self.send_data(0x44)

        self.send_command(0x37)   # set display option, these setting turn on previous function
        switch_byte = 0x00
        if monochrome:
            switch_byte = 0xFF
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)
        self.send_data(switch_byte)

        self.send_command(0x44)   # setting X direction start/end position of RAM
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x17)
        self.send_data(0x01)

        self.send_command(0x45)   # setting Y direction start/end position of RAM
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0xDF)
        self.send_data(0x01)

        self.send_command(0x22)   # Display Update Control 2
        self.send_data(0xCF)

    def clear(self):
        high = self.height
        if( self.width % 8 == 0) :
            wide =  self.width // 8
        else :
            wide =  self.width // 8 + 1

        self.send_command(0x49)
        self.send_data(0x00)
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x24)
        blanks = bytearray([0xff for e in range(0, wide)])
        for j in range(0, high):
            self.send_data_array(blanks)

        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x26)
        for j in range(0, high):
            self.send_data_array(blanks)
        blanks = None

        self.Load_LUT(0)
        self.send_command(0x22)
        self.send_data(0xC7)

        self.send_command(0x20)
        self.ReadBusy()

    # Here for reference, not actually used
    def display(self, data):
        self.send_command(0x49)
        self.send_data(0x00)

        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x24)
        for i in range(0, self.width * self.height // 8):
            temp3=0
            for j in range(0, 2):
                temp1 = data[i * 2 + j]
                for k in range(0, 2):
                    temp2 = temp1&0x03
                    if(temp2 == 0x03):
                        temp3 |= 0x01   # white
                    elif(temp2 == 0x00):
                        temp3 |= 0x00   # black
                    elif(temp2 == 0x02):
                        temp3 |= 0x01   # gray1
                    else:   # 0x01
                        temp3 |= 0x00   # gray2
                    temp3 <<= 1

                    temp1 >>= 2
                    temp2 = temp1&0x03
                    if(temp2 == 0x03):   # white
                        temp3 |= 0x01
                    elif(temp2 == 0x00):   # black
                        temp3 |= 0x00
                    elif(temp2 == 0x02):
                        temp3 |= 0x01   # gray1
                    else:   # 0x01
                        temp3 |= 0x00   # gray2

                    if (( j!=1 ) | ( k!=1 )):
                        temp3 <<= 1

                    temp1 >>= 2

            self.send_data(temp3)
        # new  data
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)


        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x26)
        for i in range(0, self.width * self.height // 8):
            temp3=0
            for j in range(0, 2):
                temp1 = data[i * 2 + j]
                for k in range(0, 2):
                    temp2 = temp1&0x03
                    if(temp2 == 0x03):
                        temp3 |= 0x01   # white
                    elif(temp2 == 0x00):
                        temp3 |= 0x00   # black
                    elif(temp2 == 0x02):
                        temp3 |= 0x00   # gray1
                    else:   # 0x01
                        temp3 |= 0x01   # gray2
                    temp3 <<= 1

                    temp1 >>= 2
                    temp2 = temp1&0x03
                    if(temp2 == 0x03):   # white
                        temp3 |= 0x01
                    elif(temp2 == 0x00):   # black
                        temp3 |= 0x00
                    elif(temp2 == 0x02):
                        temp3 |= 0x00   # gray1
                    else:   # 0x01
                        temp3 |= 0x01   # gray2

                    if (( j!=1 ) | ( k!=1 )):
                        temp3 <<= 1

                    temp1 >>= 2

            self.send_data(temp3)

        self.Load_LUT(0)

        self.send_command(0x22)
        self.send_data(0xC7)

        self.send_command(0x20)

        self.ReadBusy()

    def displayMessage(self, *args):
        # Can use simpler black/white mode for this
        self.init(True) # True black/white color mode, False for 4 colors

        # Create a small framebuffer to display several lines of text
        textBufferHeight = 12 * (1 + len(args))
        textBufferWidth = 128 # Enough pixels to fit text
        textBufferByteArray = bytearray(textBufferHeight * textBufferWidth // 8)
        image = framebuf.FrameBuffer(textBufferByteArray, textBufferWidth, textBufferHeight, framebuf.MONO_HLSB)
        image.fill(0xff)
        for h in range(0, len(args)):
            image.text(str(args[h]), 5, 12 * (1 + h), 0x00)

        # For partial updates, these 2 lines get replaced
        self.send_command(0x49)
        self.send_data(0x00)

        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x24)

        partial_blanks = bytearray([0xff for e in range((self.width - textBufferWidth) // 8)])
        for i in range(0, textBufferHeight):
            row_byte_offset = i * (textBufferWidth // 8)
            self.send_data_array(textBufferByteArray[row_byte_offset: row_byte_offset + (textBufferWidth // 8)])
            self.send_data_array(partial_blanks)
        partial_blanks = None

        full_blanks = bytearray([0xff for e in range(self.width // 8)])
        for i in range(textBufferHeight, self.height):
            self.send_data_array(full_blanks)
        full_blanks = None

        self.Load_LUT(1)

        self.send_command(0x20)
        self.ReadBusy()

    def sleep(self):
        self.send_command(0X50)
        self.send_data(0xf7)
        self.send_command(0X02)  # power off
        self.send_command(0X07)  # deep sleep
        self.send_data(0xA5)


    def process_data_block(self, data, block_number, send_response):
        if block_number == 0:
            self.init()
            # first buffer
            self.send_command(0x49)
            self.send_data(0x00)

            self.send_command(0x4E)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x4F)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x24)

            self.send_data_array(data)

            send_response(200, 'OK')

            self.data_block_count = 1
        elif block_number == 1:
            if (block_number != self.data_block_count):
                send_response(409, 'Conflict - expected block number ' + str(self.data_block_count))
                self.data_block_count = 0
                return

            # second buffer
            self.send_command(0x4E)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x4F)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x26)

            self.send_data_array(data)

            send_response(200, 'OK')

            self.Load_LUT(0)

            self.send_command(0x22)
            self.send_data(0xC7)

            self.send_command(0x20)

            self.ReadBusy()

            # self.TurnOnDisplay()
            self.data_block_count = 0
            self.delay_ms(2000)
            self.sleep()
