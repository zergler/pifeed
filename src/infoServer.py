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


class InfoServer(threading.Thread):
    """
    """
    def __init__(self, feederName):
        threading.Thread.__init__(self)
        self.feederName = feederName
        self.resource = File('/home/pi/PiFeed/')
        self.resource.putChild('', resource)
        self.factory = Site(resource)
        reactor.listenTCP(8000, self.factory)
        print('%s: twisted web server started' % (self.feederName))
        self.run()

    def run(self):
        reactor.run()
