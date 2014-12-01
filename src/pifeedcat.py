#!/usr/bin/env python

""" Controls, configures, and monitors pet feeders.

A client application allows the user to customize and control pet feeders for
manual or automatic operation. Also receives information from the pet feeders.
"""

__author__ = 'Igor Janjic, Danny Duangphachanh, Daniel Friedman'
__version__ = '0.1'

import argparse
import json
import pika
import socket
import sys

DEBUG = 0
try:
    import pdb
except ImportError as error:
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
        self.desc = 'A client application allows the user to customize and \
            control pet feeders for manual or automatic operation. Also \
            receives information from the pet feeders.'
        self.epil = 'Thank you for using %s version %s. Created by %s on %s \
            for %s.' % (self.name, self.version, self.author, self.date,
                        self.organ)

        self.daysOfWeek = ['MON', 'TUES', 'WED', 'THU', 'FRI', 'SAT',
                           'SUN', 'ALL']

        self.possibleFeeders = ['RASP1', 'RASP2']

        # Arguments help.
        self.feederHelp = 'Feeder to connect to. Allowable choices are ' + \
            ', '.join(self.possibleFeeders) + '.'
        self.helpHelp = 'Show this help message and exit.'
        self.verbHelp = 'Increase output verbosity.'
        self.manHelp = 'Manually start feeding.'
        self.nhelp = 'Number of times to keep feeding. Default is to keep the \
            feeder running indefinitely.'
        self.timeHelp = 'A list of times to feed. Allowable choices are from \
            0:00 to 23:99. Default is 12:00.'

        self.daysHelp = 'A list of days to feed. Allowable choices are ' + \
            ', '.join(self.daysOfWeek) + '. Default is ALL days of the week.'

        # Argparser.
        argParser = argparse.ArgumentParser(prog=self.name,
                                            description=self.desc,
                                            epilog=self.epil, add_help=False)
        requiredArgs = argParser.add_argument_group('Required arguments', '')
        optionalArgs = argParser.add_argument_group('Optional arguments', '')

        requiredArgs.add_argument('-f', '--feeder', type=str, dest='feeder',
                                  required=True, help=self.feederHelp,
                                  choices=self.possibleFeeders, metavar='')

        optionalArgs.add_argument('-h', '--help', action='help',
                                  help=self.helpHelp)
        optionalArgs.add_argument('-v', '--verbosity', action='count',
                                  default=0, help=self.verbHelp)
        optionalArgs.add_argument('-m', '--manual', dest='man',
                                  action='store_true', default=False,
                                  help=self.manHelp)
        optionalArgs.add_argument('-n', '--number', type=int, dest='n',
                                  default=0, help=self.nhelp, metavar='')
        optionalArgs.add_argument('-t', dest='times', default=['12:00'],
                                  nargs='+', help=self.timeHelp, metavar='')
        optionalArgs.add_argument('-d', type=str, dest='days', default=['ALL'],
                                  nargs='+', help=self.daysHelp,
                                  choices=self.daysOfWeek, metavar='')

        self.args = argParser.parse_args()


class PiFeedControl(object):
    """ Implements the PiFeedControl.
    """
    def __init__(self, verbosity, feeder, man, n, times, days):
        self.rasp1IP = 'localhost'
        self.rasp1Port = 8080
        self.rasp1Size = 1024
        self.rasp1RcvdData = 0
        self.rasp2IP = 'localhost'
        self.rasp2Port = 8080
        self.rasp2Size = 1024
        self.rasp2RcvdData = 0
        self.verbosity = verbosity
        self.config = {
            'feeder': feeder,    # Feeder to connect to
            'man': man,          # Boolean true if manual feed
            'auto': {            # Dictionary for automatic configuration
                'n': n,          # Number of times to repeat
                'times': times,  # List of times during the day to feed
                'days': days     # 7 bits bitstring high on the days to feed
            }
        }

    def feed(self):
        # If the request to configure is ready, send the message to the server.
        if self.config['feeder'] is ' RASP1':
            # Connect to RASP1.
            serverAddress = (self.rasp1IP, self.rasp1Port)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(serverAddress)
                sock.send(json.dumps(self.config))
                recvData = sock.recv(self.rasp1Size)

            except socket.error as error:
                raise ErrorSocket(self.config['feeder'], error.strerror)
            else:
                if self.verbosity >= 1:
                    print('Connected to server %s at %s.' % serverAddress)
                sock.close()

            try:
                recvDataJson = json.loads(recvData)
            except ValueError as error:
                raise ErrorInvalidResponse(self.config['feeder'], recvDataJson)


def main():
    if DEBUG:
        pdb.set_trace()
    args = PiFeedControlArgs()
    args = args.args

    try:
        pfc = PiFeedControl(args.verbosity, args.feeder, args.man, args.n,
                            args.times, args.days)
        pfc.feed()
    except ErrorSocket as error:
        print(error.msg)
    except ErrorInvalidResponse as error:
        print(error.msg)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nClosing.')


if __name__ == "__main__":
    main()
