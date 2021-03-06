#!/usr/bin/env python2.7

""" Controls, configures, and monitors pet feeders.

An application that receives connection requests from the PiFeed control
or PiFeed feeders and sends an image retrieved from the Raspberry Pi
camera to the Twisted web server.
"""

__author__ = 'Danny Duangphachanh, Igor Janjic, Daniel Friedman'

from twisted.web import server, resource
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.static import File

resource = File('/home/pi/PiFeed/src/')
resource.putChild('', resource)
factory = Site(resource)
reactor.listenTCP(8000, factory)
reactor.run()
