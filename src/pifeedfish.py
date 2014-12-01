#!/usr/bin/env python

""" jskfjlsj
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
    """ Base exception for the PiFeedFish client.
    """
    def __init__(self):
        self.msg = 'error: unspecified error has occurred'


class ErrorSocketOpen(Error):
    """ Raised when an error occurs trying to open the socket.
    """
    def __init__(self, feeder, errorMsg):
        self.msg = 'error: failed opening socket connection for %s: %s' \
            % (feeder, errorMsg)


class ErrorSocketListen(Error):
    """ Raised when an error occurs trying to listen on the socket.
    """
    def __init__(self, feeder, errorMsg):
        self.msg = 'error: failed to liste on socket for %s: %s' \
            % (feeder, errorMsg)


class PiFeedFishArgs(object):
    """ Argument parser for PiFeed.
    """
    def __init__(self):
        # Basic info.

        self.version = 1.0
        self.name = 'pifeedfish'
        self.date = '11/11/14'
        self.author = 'Igor Janjic, Danny Duangphachanh, and Daniel Friedman'
        self.organ = '[ECE 4564] Network Applications Design at Virginia Tech'
        self.desc = 'A server application for feeder RASPF1 %s (fish).'
        self.epil = 'Thank you for using %s version %s. Created by %s on %s \
            for %s.' % (self.name, self.version, self.author, self.date,
                        self.organ)

        self.daysOfWeek = ['MON', 'TUES', 'WED', 'THU', 'FRI', 'SAT',
                           'SUN', 'ALL']

        # List of possible fish feeders can be extended for future additions.
        self.possibleFeeders = ['RASPF1']

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


class PiFeedFish(object):
    """ Implements the PiFeedFish.
    """
    class Client(object):
        """ Class for accepted client.
        """
        def __init__(self, clientConn, addr, port, size, verbosity):
            """ Class constructor.
            """
            self.clientConn = clientConn
            self.addr = addr
            self.port = port
            self.size = size

        def run(self):
            """ Runs the client thread.
            """
            try:
                recvData = self.clientConn.recv(self.size)

                # Do something.
                print(recvData)
            except socket.error as error:
                raise Error(error.strerror)

    def __init__(self, verbosity, feeder, man, n, times, days):
        self.rasp1Client = None
        self.rasp1Host = 'localhost'
        self.rasp1Port = 8080
        self.rasp1Size = 1024
        self.rasp1Backlog = 5
        self.rasp1RcvdData = 0

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

    def openSocket(self):
        """ Opens a stream socket.
        """
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.rasp1Host, self.rasp1Port))
            self.server.listen(self.rasp1Backlog)
        except socket.error as error:
            raise ErrorSocketOpen(self.config['feeder'], error.strerror)
        else:
            if self.verbosity >= 1:
                print('Starting config server for %s at %s, port %s.' % (self.config['feeder'], self.rasp1Host, self.rasp1Port))

    def run(self):
        """ Runs the server.
        """
        # Make sure that a socket is open before running.
        if self.server is None:
            raise Error()

        # Listen for clients and try to connect.
        while True:
            try:
                self.server.listen(self.rasp1Backlog)
                (clientConn, (clientAddr, clientPort)) = \
                    self.server.accept()
            except socket.error as error:
                raise Error()
            else:
                if self.verbosity >= 1:
                    print('%s: connected to client %s:%s.'
                          % (self.config['feeder'], clientAddr, clientPort))

            # Receive the request.
            newClient = self.Client(clientConn, clientAddr,
                                    clientPort, self.rasp1Size, self.verbosity)
            newClient.run()


def main():
    if DEBUG:
        pdb.set_trace()
    args = PiFeedFishArgs()
    args = args.args

    try:
        pfc = PiFeedFish(args.verbosity, args.feeder, args.man, args.n,
                         args.times, args.days)
        pfc.openSocket()
        pfc.run()
    except ErrorSocketOpen as error:
        print(error.msg)
    except ErrorSocketListen as error:
        print(error.msg)
        sys.exit(1)
    except Error as error:
        print(error.msg)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nClosing.')


if __name__ == "__main__":
    main()
