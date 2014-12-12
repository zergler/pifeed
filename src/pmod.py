#!/usr/bin/env python

""" Library to interface with the Digilent PMOD display using UART.
"""

__author__ = 'Igor Janjic'
__version__ = '0.1'


import enum
import time
import serial


class AccessType(enum.Enum):
    UART = 0
    SPI = 1
    TWI = 2


class PMOD:
    """ Implements interface to Digilent PMOD display.
    """
    def __init__(self, accessType):
        # Dimensions of the display.
        self.rows = 2
        self.cols = 16

        # Definition of commands that can be sent to the PMOD.
        self.ESC = chr(0x1B)
        self.BRACKET = '['
        self.RESET = '*'                # reset (cycles power)
        self.CURSOR_POS_SET = 'H'       # set cursor position
        self.CURSOR_POS_SAVE = 's'      # save cursor position
        self.CURSOR_POS_RESTORE = 'u'   # restore saved cursor position
        self.CURSOR_MODE_SET = 'c'      # set cursor mode
        self.CURSOR_MODE_SAVE = 'n'     # save cursor mode to EEPROM
        self.ERASE_INLINE = 'K'         # erase within line
        self.ERASE_FIELD = 'N'          # erase field in current line
        self.SCROLL_LEFT = '@'          # scroll left
        self.SCROLL_RIGHT = 'A'         # scroll right
        self.DISP_EN = 'e'              # enable backlight for dislay
        self.DISP_CLEAR = 'j'           # clear display and home cursor
        self.DISP_MODE_SET = 'h'        # set display mode
        self.DISP_MODE_SAVE = 'o'       # save display mode to EEPROM
        self.BAUD_RATE_SAVE = 'b'       # save baud rate value in EEPROM
        self.TABLE_PRGM = 'p'           # program character table into LCD
        self.TABLE_SAVE = 't'           # save RAM character table to EEPROM
        self.TABLE_LOAD = 'l'           # load EEPROM character table to RAM
        self.CHAR_DEF = 'd'             # define user programmable character
        self.COMM_MODE_SAVE = 'm'       # save communication mode to EEPROM
        self.TWI_ADDR_SAVE = 'a'        # save TWI address in EEPROM
        self.EEPROM_WRITE_EN = 'w'      # enable write to EEPROM

        # Access configuration.
        self.accessType = accessType
        self.accessPortLaptop = '/dev/ttyUSB0'
        self.accessPortPi = '/dev/ttyAMA0'
        self.baudRate = 9600

        # When an instruction is sent to PMOD, it must first receive the
        # correct instruction header. Once the header is sent, the following
        # flag is set. If a message is written to the PMOD while the flag is
        # set, an error will occur.
        # self.instrReady = False

        # Connect to UART.
        self.ser = serial.Serial(self.accessPortLaptop, self.baudRate)

    def write(self, msg, row, col):
        """ Writes a message to the PMOD at the given row and column. Breaks up
            the string given in msg and writes it out to the PMOD two bytes at
            a time.
        """
        try:
            if self.accessType is AccessType.UART:
                # Make sure the message can fit on the display.
                if row > self.rows:
                    raise ErrorRangeRow(row)
                if len(msg) > self.cols:
                    raise ErrorRangeCol(len(msg))

                # Set the position.
                self.dispClear()
                # self.cursorPosSet(row, col)

                # Write it out.
                for char in msg:
                    self.writeChar(char)

        except ErrorRangeRow as e:
            print(e.msg)
        except ErrorRangeCol as e:
            print(e.msg)

    def writeChar(self, char):
        """ Writes a character to the PMOD.
        """
        if self.accessType is AccessType.UART:
            if len(char) > 1:
                raise ErrorWrite()
            self.ser.write(char)

    def writeInstrHeader(self):
        """ PMOD expects to get the character sequence escape followed by a bracket
        before the instruction can be sent.
        """
        self.writeChar(self.ESC)
        self.writeChar(self.BRACKET)

    def reset(self):
        """ Reset PMOD. Equivalent to cycling the power.
        """
        self.writeInstrHeader()
        self.writeChar(self.RESET)

    def cursorPosSet(self, row, col):
        """ Sets the cursor position to the given row column.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(chr(row))
            self.writeChar(',')
            self.writeChar(chr(col))
            self.writeChar(self.CURSOR_POS_SET)
        except ErrorWrite as e:
            print(e.msg)

    def cursorPosSave(self):
        """ Saves the current cursor position.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(self.CURSOR_POS_SAVE)
        except ErrorWrite as e:
            print(e.msg)

    def cursorPosRestore(self):
        """ Restores the saved cursor position.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(self.CURSOR_POS_RESTORE)
        except ErrorWrite as e:
            print(e.msg)

    def cursorModeSet(self, mode):
        """ Sets the cursor mode.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(chr(mode))
            self.writeChar(self.CURSOR_MODE_SET)
        except ErrorWrite as e:
            print(e.msg)

    def cursorModeSave(self, mode):
        """ Saves the cursor mode to EEPROM.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(chr(mode))
            self.writeChar(self.CURSOR_MODE_SAVE)
        except ErrorWrite as e:
            print(e.msg)

    def eraseInline(self, mode):
        """ Erases within line based on the mode.

            If mode is 0, erases from the current position to end of the line.
            If mode is 1, erases from the start of the line to the current
            position. If mode is 2, erases the entire line.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(chr(mode))
            self.writeChar(self.CURSOR_MODE_SAVE)
        except ErrorWrite as e:
            print(e.msg)

    def eraseField(self, chars):
        """ Erases field in the current line where chars is the number of chars
            to erase starting at the current position.
        """
        pass

    def scrollLeft(self, cols):
        """ Scrolls left by the selected number of columns.
        """
        pass

    def scrollRight(self, cols):
        """ Scrolls right by the selected number of columns.
        """
        pass

    def dispClear(self):
        """ Clears the display and home the cursor.
        """
        try:
            self.writeInstrHeader()
            self.writeChar(self.DISP_CLEAR)
        except ErrorWrite as e:
            print(e.msg)

    def dispModeSet(self, mode):
        """ Sets the display mode.
        """
        pass

    def dispModeSave(self, mode):
        """ Saves the display mode to EEPROM.
        """
        pass

    def baudRateSave(self, baud):
        """ Saves the baud rate to EEPROM.
        """
        pass

    def tablePrgrm(self, table):
        """ Programs the character table into the LCD.
        """
        pass

    def tableSave(self, table):
        """ Saves the RAM character table to EEPROM.
        """
        pass

    def tableLoad(self, table):
        """ Loads the EEPROM character table to RAM.
        """
        pass

    def charDef(self, char, pos):
        """ Defines a user programmable character.
        """
        pass

    def commModeSave(self, mode):
        """ Saves the communication mode to EEPROM.
        """
        pass

    def twiAddrSave(self, addr):
        """ Saves the TWI address to EEPROM.
        """
        pass

    def eepromWriteEn(self):
        """ Enables writign to EEPROM.
        """
        pass


class ErrorPMOD(Exception):
    """ Base exception class for PMOD.
    """
    def __init__(self, msg):
        self.msg = 'error: %s' % msg


class ErrorWrite(ErrorPMOD):
    """ Failed writing to the display.
    """
    def __init__(self, msg=''):
        self.msg = 'error: failed writing to the display'
        if msg != '':
            self.msg = '%s: %s' % (self.msg, msg)

class ErrorRangeRow(ErrorPMOD):
    """ Row is not within range (0, 2).
    """
    def __init__(self, row):
        self.msg = "error: selected row '%s' is not within range (0, 2)" % row


class ErrorRangeCol(ErrorPMOD):
    """ Column is is not within range (0, 39).
    """
    def __init__(self, col):
        self.msg = "error: selected column '%s' is not within range (0, 39)" \
            % col


class ErrorRangeModeErase(ErrorPMOD):
    """ Erase type is not within range (0, 2).
    """
    def __init__(self, eraseMode):
        self.msg = "error: selected erase type '%s' is not within range (0, \
            2)" % eraseMode


class ErrorRangeModeBaudRate(ErrorPMOD):
    """ Bud rate mode is not within range (0, 6).
    """
    def __init__(self, baudRateMode):
        self.msg = "error: selected baud rate mode '%s' is not within range s\
            (0, 6)" % baudRateMode


class ErrorRangeTable(ErrorPMOD):
    """ Table is not within range (0, 3).
    """
    def __init__(self):
        self.msg = 'error: table is not within range (0, 3)'


class ErrorRangeModeComm(ErrorPMOD):
    """ Communication mode is not within range (0, 7).
    """
    def __init__(self, commMode):
        self.msg = "error: communication mode '%s' is not within range (0, \
            7)" % commMode


class ErrorRangeModeCursor(ErrorPMOD):
    """ Cursor mode is not within range (0, 2).
    """
    def __init__(self, cursorMode):
        self.msg = "error: cursor mode '%s' is not within range (0, 2)" \
            % cursorMode


class ErrorRangeModeDisplay(ErrorPMOD):
    """ Display mode is not within range (0, 3).
    """
    def __init__(self, dispMode):
        self.msg = "error: display mode '%s' is not within range (0, 3)" \
            % dispMode


class ErrorRangeCharPos(ErrorPMOD):
    """ Character position in memory is not within range (0, 7).
    """
    def __init__(self, charPos):
        self.msg = "error: character position '%s' is not within range (0, \
            7)" % charPos
