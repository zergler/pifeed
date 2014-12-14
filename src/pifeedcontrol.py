#!/usr/bin/env python2.7

""" Controls, configures, and monitors pet feeders.

A client application allows the user to customize and control pet feeders for
manual or automatic operation. Also receives information from the pet feeders.
"""

__author__ = 'Igor Janjic, Danny Duangphachanh, Daniel Friedman'
__version__ = '0.1'

import argparse
import json
import socket
import sys

DEBUG = 0
try:
    import pdb
except ImportError:
    DEBUG = 0


class Error(Exception):
    """ Base exception for the PiFeedControl client.
    """
    pass


class ErrorSocket(Error):
    """ Raised when there is a bad socket connection.
    """
    def __init__(self, feeder, errorMsg):
        self.msg = 'error: bad socket connection to feeder %s: %s' \
            % (feeder, errorMsg)


class ErrorInvalidResponse(Error):
    """ Raised when the application receives a network response of an invalid
        format.
    """
    def __init__(self, feeder, response):
        self.msg = 'error: invalid response from feeder %s: %s' \
            % (feeder, response)


class PiFeedControlArgs(object):
    """ Argument parser for PiFeed.
    """
    def __init__(self):
        # Basic info.

        self.version = 1.0
        self.name = 'pifeedcontrol'
        self.date = '11/11/14'
        self.author = 'Igor Janjic, Danny Duangphachanh, and Daniel Friedman'
        self.organ = '[ECE 4564] Network Applications Design at Virginia Tech'
        self.desc = 'A client application that interfaces with the feeders.'
        self.epil = 'Thank you for using %s version %s. Created by %s on %s for %s.' % (self.name, self.version, self.author, self.date, self.organ)

        self.daysOfWeek = ['MON', 'TUES', 'WED', 'THU', 'FRI', 'SAT', 'SUN', 'ALL', 'NONE']

        # List of possible fish feeders can be extended for future additions.
        self.possibleFeeders = ['RASPF1', 'RASPC1']

        # Arguments help.
        self.feederHelp = 'Feeder to connect to. Allowable choices are ' + ', '.join(self.possibleFeeders) + '.'
        self.helpHelp = 'Show this help message and exit.'
        self.verbHelp = 'Increase output verbosity.'
        self.manHelp = 'Manually start feeding.'
        self.repeatHelp = 'Number of times to keep feeding. Default is to keep the feeder running indefinitely.'
        self.timeHelp = 'A list of times to feed. Allowable choices are from 0:00 to 23:99. Default is 12:00.'
        self.daysHelp = 'A list of days to feed. Allowable choices are ' + ', '.join(self.daysOfWeek) + '. Default is ALL days of the week.'
        self.cameraHelp = 'Frames per second of the camera.'
        self.sensorHelp = 'Number of times to query the temperature sensor per second.'

        # Argparser.
        self.argParser = argparse.ArgumentParser(prog=self.name, description=self.desc, epilog=self.epil, add_help=False)
        requiredArgs = self.argParser.add_argument_group('Required arguments', '')
        optionalArgs = self.argParser.add_argument_group('Optional arguments', '')

        requiredArgs.add_argument('-f', '--feeder', type=str, dest='feeder', required=True, help=self.feederHelp, choices=self.possibleFeeders, metavar='\b')
        optionalArgs.add_argument('-h', '--help', action='help', help=self.helpHelp)
        optionalArgs.add_argument('-v', '--verbosity', action='count', default=0, help=self.verbHelp)
        optionalArgs.add_argument('-m', '--manual', dest='man', action='store_true', default=False, help=self.manHelp)
        optionalArgs.add_argument('-r', '--repeat', type=int, dest='repeat', default=0, help=self.repeatHelp, metavar='\b')
        optionalArgs.add_argument('-c', '--camera', type=int, dest='camera', default=1, help=self.cameraHelp, metavar='\b')
        optionalArgs.add_argument('-s', '--sensor', type=int, dest='sensor', default=0, help=self.sensorHelp, metavar='\b')
        optionalArgs.add_argument('-t', dest='times', default=[], nargs='+', help=self.timeHelp, metavar='[\b')
        optionalArgs.add_argument('-d', type=str, dest='days', default=[], nargs='+', help=self.daysHelp, choices=self.daysOfWeek, metavar='[\b')

    def parse(self):
        self.args = self.argParser.parse_args()


class PiFeedControl(object):
    """ Implements the control module.
    """
    def __init__(self, verbosity, feeder, man, repeat, times, days, camera, sensor):
        self.rasp1Host = 'localhost'
        self.rasp1Port = 8080
        self.rasp1Size = 1024
        self.rasp1RcvdData = 0
        self.rasp2Host = 'localhost'
        self.rasp2Port = 8080
        self.rasp2Size = 1024
        self.rasp2RcvdData = 0
        self.verbosity = verbosity
        self.config = {
            'feeder': feeder,      # Feeder to connect to
            'man': man,            # Boolean true if manual feed
            'camera': camera,      # Frames per second of the camera
            'sensor': sensor,      # Number of times to read temp sensor
            'auto': {              # Dictionary for automatic configuration
                'repeat': repeat,  # Number of times to repeat
                'times': times,    # List of times during the day to feed
                'days': days       # 7 bits bitstring high on the days to feed
            }
        }

    def feed(self):
        # If the request to configure is ready, send the message to the server.
        if self.config['feeder'] == 'RASPF1':
            # Connect to RASPF1.
            serverAddress = (self.rasp1Host, self.rasp1Port)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(serverAddress)
                sock.send(json.dumps(self.config))
            except socket.error as e:
                raise ErrorSocket(self.config['feeder'], e.strerror)
            if self.verbosity >= 1:
                print('Connected to server %s at %s.' % serverAddress)

            try:
                while True:
                    recvData = sock.recv(self.rasp1Size)
                    recvDataJson = json.loads(recvData)
                    print(recvDataJson)
                    # outfile = open('new.jpg', 'wb')
                    # outfile.write(recvData)

                sock.close()
            except socket.error as e:
                raise ErrorSocket(self.config['feeder'], e.strerror)
            except ValueError:
                raise ErrorInvalidResponse(self.config['feeder'], recvData)


def main():
    if DEBUG:
        pdb.set_trace()
    args = PiFeedControlArgs()
    args.parse()
    args = args.args

    try:
        pfc = PiFeedControl(args.verbosity, args.feeder, args.man, args.repeat, args.times, args.days, args.camera, args.sensor)
        pfc.feed()
    except ErrorSocket as e:
        print(e.msg)
    except ErrorInvalidResponse as e:
        print(e.msg)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nClosing.')


if __name__ == "__main__":
    main()
