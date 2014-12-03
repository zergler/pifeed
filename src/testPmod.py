#!/usr/bin/env python2.7

import pmod


def testUART():
    m_accessType = pmod.AccessType.UART
    m_pmod = pmod.PMOD(m_accessType)
    m_pmod.write("lslsf")


if __name__ == '__main__':
    testUART()
