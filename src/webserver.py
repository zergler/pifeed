#!/usr/bin/env python2.7

""" Controls, configures, and monitors pet feeders.

A client application allows the user to customize and control pet feeders for
manual or automatic operation. Also receives information from the pet feeders.
"""

__author__ = 'daduang'

from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor

import os
import signal

# Protocol for managing PiFeed commands
class webserv(Protocol):
    def connectionMade(self):
        self.factory.clients.append(self)
        print "clients are ", self.factory.clients

    def connectionLost(self, reason):
        print "connection lost ", self.factory.clients
        self.factory.clients.remove(self)

    def dataReceived(self, data):
        msg = ""
        if (data == "-d"):
            msg = "add/remove a day"
            print msg
            msg = ""
        if (data == "-t"):
            msg = "add/remove a time"
            print msg
            msg = ""

    # def dataReceived(self, data):
    #     # Check for days of the week
    #     if data == "-d":
    #         # Add/Remove Monday
    #         if data == "MON":
    #             exit(1)
    #         # Add/Remove Tuesday
    #         if data == "TUE":
    #             exit(1)
    #
    #         # Add/Remove Wednesday
    #         if data == "WED":
    #             exit(1)
    #
    #         # Add/Remove Thursday
    #         if data == "THU":
    #             exit(1)
    #
    #         # Add/Remove Friday
    #         if data == "FRI":
    #             exit(1)
    #
    #         # Add/Remove Saturday
    #         if data == "SAT":
    #             exit(1)
    #
    #         # Add/Remove Sunday
    #         if data == "SUN":
    #             exit(1)
    #
    #     # Check for times of the day
    #     if data == "-t":
    #         exit(1)




# Twisted initialization
factory = Factory()

# Assign to Twisted the protocol managing commands
factory.protocol = webserv

factory.clients = []

# Set the server to listen on all network interfaces port 8000
reactor.listenTCP(8080, factory)

print "Twisted web server started"

# Starts TCP server, which will wait for connections to serve
reactor.run()