from machine import Pin, SPI
import framebuf
import gc
import utime

RST_PIN         = 12
DC_PIN          = 8
CS_PIN          = 9
BUSY_PIN        = 13

class EPD:

    def __init__(self, epd_width, epd_height):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)

        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.width = epd_width
        self.height = epd_height

        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

        self.data_block_count = 0
        self.expected_block_count = 0

        # self.init()

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        # Also do this
        self.data_block_count = 0

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def send_data_array(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte(data)
        self.digital_write(self.cs_pin, 1)

    def init(self, *args):
        pass

    def clear(self):
        pass

    def display(self, image):
        pass
    
    def displayMessage(self, *args):
        pass

    def sleep(self):
        pass

    def process_data_block(self, data, block_number, send_response):
        pass


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
        colorblack = 0xFF
        colorred = 0xFF
        self.send_command(0x10)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(colorblack)
        self.send_command(0x13)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(colorred)

        self.TurnOnDisplay()

    # Here for reference, not actually used
    def display(self):
        self.send_command(0x10)
        for j in range(0, self.height):
            for i in range(0, int(self.width // 8)):
                self.send_data(self.buffer_black[i + j * int(self.width // 8)])
        self.send_command(0x13)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(self.buffer_red[i + j * int(self.width // 8)])

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
            for i in range(0, int(textBufferWidth // 8)):
                self.send_data(textBufferByteArray[i + j * int(textBufferWidth // 8)])
        image = None
        textBufferByteArray = None
        gc.collect()
        # Rest of black image
        for j in range(textBufferHeight, self.height):
            for i in range(0, int(self.width // 8)):
                self.send_data(0xff)
        self.send_command(0x13)
        # Red image is blank
        for j in range(0, self.height):
            for i in range(0, int(self.width // 8)):
                self.send_data(0xff)
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
        if (block_number == 0):
            self.init()
            # black buffer
            self.send_command(0x10)
            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])
            send_response(200, 'OK')
            self.data_block_count = 1
        elif (block_number != self.data_block_count):
            send_response(409, 'Conflict - expected block number ' + str(self.data_block_count))
            self.data_block_count = 0
            return
        elif (block_number == 1):
            # red buffer
            self.send_command(0x13)
            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])
            send_response(200, 'OK')

            self.TurnOnDisplay()
            self.data_block_count = 0
            self.delay_ms(2000)
            self.sleep()


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
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0Xff)

        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x26)
        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(0Xff)

        self.Load_LUT(0)
        self.send_command(0x22)
        self.send_data(0xC7)

        self.send_command(0x20)
        self.ReadBusy()

    # Here for reference, not actually used
    def display(self, Image):
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
                temp1 = Image[i*2+j]
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
                temp1 = Image[i*2+j]
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
        for j in range(0, self.height):
            for i in range(0, int(self.width // 8)):
                if i < int(textBufferWidth // 8) and j < int(textBufferHeight):
                    self.send_data(textBufferByteArray[i + j * int(textBufferWidth // 8)])
                else:
                    self.send_data(0xff)

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

            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])
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
            
            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])

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
        blanks = [color2 for e in range(0, int(self.width // 2))]
        for j in range(0, self.height):
            self.send_data_array(blanks)
        self.send_command(0x04)   # 0x04
        self.BusyHigh()
        self.send_command(0x12)   # 0x12
        self.BusyHigh()
        self.send_command(0x02)   # 0x02
        self.BusyLow()
        self.delay_ms(500)

    # For reference, not used
    def display(self, image):

        self.send_command(0x61)   # Set Resolution setting
        self.send_data(0x02)
        self.send_data(0x58)
        self.send_data(0x01)
        self.send_data(0xC0)
        self.send_command(0x10)
        for i in range(0, self.height):
            for j in range(0, int(self.width // 2)):
                self.send_data(image[j+(int(self.width // 2)*i)])

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
        partial_blanks = [0x77 for e in range(0, int(self.width // 2 - halfBufferWidth))]
        for i in range(0, textBufferHeight): # self.height):
            row_byte_offset = i * halfBufferWidth
            self.send_data_array(textBufferByteArray[row_byte_offset : row_byte_offset + halfBufferWidth])
            self.send_data_array(partial_blanks)
        full_blanks = [0x77 for e in range(0, int(self.width // 2))]
        for i in range(textBufferHeight, self.height):
            self.send_data_array(full_blanks)

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
        for i in range(0, self.height / 8):
            self.send_data_array(data[index : index + int(self.width // 2)])
            index += int(self.width // 2)

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