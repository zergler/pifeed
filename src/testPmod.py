#!/usr/bin/env python2.7

import pmod


def testUART():
    m_accessType = pmod.AccessType.UART
    m_pmod = pmod.PMOD(m_accessType)
    m_pmod.dispClear()
    blah = chr(0xFE) + chr(0x00) + chr(0x32) + chr(0x0A) + chr(0x05) + chr(0x0A) + chr(0xFF)
    m_pmod.write(blah, 0, 0)


if __name__ == '__main__':
    testUART()
