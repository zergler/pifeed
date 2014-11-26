#!/usr/bin/env python

""" Library to interface with the Digilent PMOD display using UART.
"""

__author__ = 'Igor Janjic'
__version__ = '0.1'


class PMOD:
    """ Implements interface to Digilent PMOD display.
    """
    def __init__(self):
        # Definition of commands that can be sent to the PMOD.
        self.ESC = 0x1B                 # ^[
        self.BRACKET = 0x5B             # [
        self.RESET = 0x2A               # *: reset (cycles power)
        self.CURSOR_SET = 0x48          # H: set cursor position
        self.CURSOR_SAVE = 0x73         # s: save cursor position
        self.CURSOR_MODE = 0x63         # c: set cursor mode
        self.CURSOR_RESTORE = 0x75      # u: restore saved cursor position
        self.ERASE_INLINE = 0x4B        # K: erase within line
        self.ERASE_FIELD = 0x4E         # N: erase field in current line
        self.SCROLL_LEFT = 0x40         # @: scroll left
        self.SCROLL_RIGHT = 0x41        # A: scroll right
        self.DISP_EN = 0x65             # e: enable backlight for dislay
        self.DISP_CLEAR = 0x6A          # j: clear display and home cursor
        self.DISP_MODE = 0x68           # h: set display mode
        self.DISP_MODE_SAVE = 0x6F      # o: save display mode to EEPROM
        self.BAUD_RATE_SAVE = 0x62      # b: save baud rate value in EEPROM
        self.CHAR_PRGM = 0x70           # p: program character table into LCD
        self.CHAR_SAVE = 0x74           # t: save RAM character table to EEPROM
        self.CHAR_LOAD = 0x6C           # l: load EEPROM character table to RAM
        self.CHAR_DEF = 0x64            # d: define user programmable character
        self.COMM_MODE_SAVE = 0x6D      # m: save communication mode to EEPROM
        self.TWI_ADDR_SAVE = 0x61       # a: save TWI address in EEPROM
        self.EEPROM_WRITE_EN = 0x77     # w: enable write to EEPROM
        self.CURSOR_MODE_SAVE = 0x6E    # n: save cursor mode to EEPROM

        # Parameters for communication ports.
        self.PAR_ACCESS_DSPI0 = 0
        self.PAR_ACCESS_DSPI1 = 1
        self.PAR_SPD_MAX = 625000


class ErrorPMOD(Exception):
    """ Base exception class for PMOD.
    """
    pass


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
        self.msg = "error: display mode '%s' is not within range (0, 3)." \
            % dispMode


class ErrorRangeCharPos(ErrorPMOD):
    """ Character position in memory is not within range (0, 7).
    """
    def __init__(self, charPos):
        self.msg = "error: character position '%s' is not within range (0, \
            7)" % charPos
