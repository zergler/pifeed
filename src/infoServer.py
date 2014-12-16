#!/usr/bin/env python2.7

""" Controls, configures, and monitors pet feeders.

An application that receives connection requests from the PiFeed control
or PiFeed feeders and sends an image retrieved from the Raspberry Pi
camera to the Twisted web server.
"""

__author__ = 'Danny Duangphachanh, Igor Janjic, Daniel Friedman'

import threading
from twisted.web import resource
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.static import File


class InfoServer():
    """
    """
    def __init__(self, feederName, lockCamera, lockSensor):
        #threading.Thread.__init__(self)
        # lockCamera.acquire()
        # lockSensor.acquire()
        feederName = feederName
        resource = File('/home/pi/PiFeed/src/')
        resource.putChild('', resource)
        factory = Site(resource)
        reactor.listenTCP(8000, factory)
        print('%s: twisted web server started' % (feederName))
        reactor.run()
        # lockSensor.release()
        # lockCamera.release()

def main():
    lockCamera = threading.Lock()
    lockSensor = threading.Lock()
    infoServer = InfoServer('RASPF1', lockCamera, lockSensor)
    #infoServer.start()

if __name__ == '__main__':
    main()
