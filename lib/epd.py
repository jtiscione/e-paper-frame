from machine import Pin, SPI
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

    def init(self):
        pass

    def clear(self):
        pass

    def display(self, image):
        pass

    def sleep(self):
        pass

    def process_data_block(self, data):
        pass


class EPD_2in9_B(EPD):

    def __init__(self):
        super().__init__(128, 296)

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

    def init(self):
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

    def display(self):
        self.send_command(0x10)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(self.buffer_black[i + j * int(self.width / 8)])
        self.send_command(0x13)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(self.buffer_red[i + j * int(self.width / 8)])

        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0X02) # power off
        self.ReadBusy()
        self.send_command(0X07) # deep sleep
        self.send_data(0xA5)

        self.delay_ms(2000)
        self.module_exit()

    def process_data_block(self, data):
        if (self.data_block_count == 0):
            self.init()
            # black buffer
            self.send_command(0x10)
            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])
            self.data_block_count = 1
        elif (self.data_block_count == 1):
            # red buffer
            self.send_command(0x13)
            for j in range(0, self.height):
                for i in range(0, int(self.width // 8)):
                    self.send_data(data[i + j * int(self.width // 8)])

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

    def init(self):
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
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)

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

    def sleep(self):
        self.send_command(0X50)
        self.send_data(0xf7)
        self.send_command(0X02)  # power off
        self.send_command(0X07)  # deep sleep
        self.send_data(0xA5)


    def process_data_block(self, data):
        if (self.data_block_count == 0):
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

            self.data_block_count = 1
        elif (self.data_block_count == 1):
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

            
            self.Load_LUT(0)

            self.send_command(0x22)
            self.send_data(0xC7)

            self.send_command(0x20)

            self.ReadBusy()

            # self.TurnOnDisplay()
            self.data_block_count = 0
            self.delay_ms(2000)
            self.sleep()
