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
import threading

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
        self.msg = 'error: failed to listen on socket for %s: %s' \
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
        self.repeathelp = 'Number of times to keep feeding. Default is to keep the \
            feeder running indefinitely.'
        self.cameraHelp = 'Frames per second of the camera.'
        self.sensorHelp = 'Number of times to query the temperature sensor per \
            second.'
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
        optionalArgs.add_argument('-n', '--number', type=int, dest='repeat',
                                  default=0, help=self.repeathelp, metavar='')
        optionalArgs.add_argument('-t', dest='times', default=['12:00'],
                                  nargs='+', help=self.timeHelp, metavar='')
        optionalArgs.add_argument('-d', type=str, dest='days', default=['ALL'],
                                  nargs='+', help=self.daysHelp,
                                  choices=self.daysOfWeek, metavar='')
        optionalArgs.add_argument('-c', '--camera', type=int, dest='camera',
                                  default=0, help=self.cameraHelp)
        optionalArgs.add_argument('-s', '--sensor', type=int, dest='sensor',
                                  default=0, help=self.sensorHelp)

        self.args = argParser.parse_args()


class PiFeedFish(object):
    """ Implements the PiFeedFish.
    """
    class Client(object):
        """ Class for accepted client.
        """
        def __init__(self, feeder, conn, addr, port, size, verbosity):
            """ Class constructor.
            """
            self.feeder = feeder
            self.conn = conn
            self.addr = addr
            self.port = port
            self.size = size

        def run(self):
            """ Runs the client thread.
            """
            try:
                recvData = self.conn.recv(self.size)

                # Write the new configuration to the rc file while honoring
                # manual requests.
                print('Receiving request from client %s:%s:'
                      % (self.addr, self.port))
                print(recvData)
                with open(self.feeder + '.config', 'w') as f:
                    json.dump(json.loads(recvData), f, sort_keys=True,
                              indent=4, ensure_ascii=True)
            except socket.error as error:
                raise Error(error.strerror)

    class Camera(threading.Thread):
        """ Class for the camera.
        """
        def __init__(self, event, camera):
            threading.Thread.__init__(self)
            self.event = event
            self.camera = camera
            self.image = None

        def run(self):
            while not self.event.wait(self.camera):
                # print("my thread camera")
                self.capture()

        def capture(self):
            pass

    class Sensor(threading.Thread):
        """ Class for the temperature sensor.
        """
        def __init__(self, event, sensor):
            threading.Thread.__init__(self)
            self.stopped = event
            self.sensor = sensor

        def run(self):
            while not self.stopped.wait(self.sensor):
                # print("my thread temp sensor")
                self.query()

        def query(self):
            pass

    def __init__(self, verbosity, feeder, man, repeat, times, days, camera,
                 sensor):
        self.rasp1Client = None
        self.rasp1Host = 'localhost'
        self.rasp1Port = 8080
        self.rasp1Size = 1024
        self.rasp1Backlog = 5
        self.rasp1RcvdData = 0

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
        self.response = {
            'image': None,         # Latest image that was captured
            'sensor': None         # Latest temperature reading
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
                print('Starting config server for %s at %s, port %s.'
                      % (self.config['feeder'], self.rasp1Host,
                         self.rasp1Port))

    def run(self):
        """ Runs the server.
        """
        # Make sure that a socket is open before running.
        if self.server is None:
            raise Error()

        # Start the threads that will control the hardware.
        cameraEvent = threading.Event()
        sensorEvent = threading.Event()
        self.camera = self.Camera(cameraEvent, self.config['camera'])
        self.sensor = self.Sensor(sensorEvent, self.config['sensor'])
        self.camera.daemon = True
        self.sensor.daemon = True
        self.camera.start()
        self.sensor.start()

        # Listen for clients and try to connect.
        while True:
            try:
                self.server.listen(self.rasp1Backlog)
                (clientConn, (clientAddr, clientPort)) = \
                    self.server.accept()
            except socket.error as error:
                raise Error(error.strerror)
            else:
                if self.verbosity >= 1:
                    print('%s: connected to client %s:%s.'
                          % (self.config['feeder'], clientAddr, clientPort))

            # Receive the request and write configuration to file..
            try:
                recvData = clientConn.recv(self.rasp1Size)

                # Write the new configuration to the rc file while honoring
                # manual requests.
                print('Receiving request from client %s:%s:'
                      % (clientAddr, clientPort))
                print(recvData)
                with open(self.config['feeder'] + '.config', 'w') as f:
                    recvDataJson = json.loads(recvData)
                    json.dump(recvDataJson, f, sort_keys=True, indent=4,
                              ensure_ascii=True)
            except socket.error as error:
                raise Error(error.strerror)
            except ValueError as error:
                raise Error(error.strerror)


def main():
    if DEBUG:
        pdb.set_trace()
    args = PiFeedFishArgs()
    args = args.args

    try:
        pff = PiFeedFish(args.verbosity, args.feeder, args.man, args.repeat,
                         args.times, args.days, args.camera, args.sensor)
        pff.openSocket()
        pff.run()
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
        sys.exit(1)


if __name__ == "__main__":
    main()
