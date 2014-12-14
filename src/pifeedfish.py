#!/usr/bin/env python2.7

""" jskfjlsj
"""

__author__ = 'Igor Janjic, Danny Duangphachanh, Daniel Friedman'
__version__ = '0.1'

import argparse
import calendar
import datetime
import json
import sched
import socket
import sys
import time
import threading
import dateutil

DEBUG = 0
try:
    import pdb
except ImportError:
    DEBUG = 0


class Error(Exception):
    """ Base exception for the module.
    """
    def __init__(self, msg):
        self.msg = 'error: %s' % msg


class ErrorSocketOpen(Error):
    """ Raised when an error occurs trying to open the socket.
    """
    def __init__(self, feeder, errorMsg):
        self.msg = 'error: failed opening socket connection for %s: %s' % (feeder, errorMsg)


class ErrorSocketListen(Error):
    """ Raised when an error occurs trying to listen on the socket.
    """
    def __init__(self, feeder, errorMsg):
        self.msg = 'error: failed to listen on socket for %s: %s' % (feeder, errorMsg)


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
        self.desc = 'A server application for feeder RASPF1.'
        self.epil = 'Thank you for using %s version %s. Created by %s on %s for %s.' % (self.name, self.version, self.author, self.date, self.organ)

        self.daysOfWeek = ['MON', 'TUES', 'WED', 'THU', 'FRI', 'SAT', 'SUN', 'ALL', 'NONE']

        # List of possible fish feeders can be extended for future additions.
        self.possibleFeeders = ['RASPF1']

        # Arguments help.
        self.feederHelp = 'Feeder to connect to. Allowable choices are ' + ', '.join(self.possibleFeeders) + '.'
        self.helpHelp = 'Show this help message and exit.'
        self.verbHelp = 'Increase output verbosity.'
        self.manHelp = 'Manually start feeding.'
        self.repeathelp = 'Number of times to keep feeding. Default is to keep the feeder running indefinitely.'
        self.timeHelp = 'A list of times to feed. Allowable choices are from 0:00 to 23:99. Default is 12:00.'
        self.daysHelp = 'A list of days to feed. Allowable choices are ' + ', '.join(self.daysOfWeek) + '. Default is ALL days of the week.'
        self.cameraHelp = 'Frames per second of the camera.'
        self.sensorHelp = 'Number of times to query the temperature sensor per second.'

        # Argparser.
        self.argParser = argparse.ArgumentParser(prog=self.name, description=self.desc, epilog=self.epil, add_help=False)
        requiredArgs = self.argParser.add_argument_group('Required arguments', '')
        optionalArgs = self.argParser.add_argument_group('Optional arguments', '')

        requiredArgs.add_argument('-f', '--feeder', type=str, dest='feeder', required=True, help=self.feederHelp, choices=self.possibleFeeders,
                                  metavar='\b')
        optionalArgs.add_argument('-h', '--help', action='help', help=self.helpHelp)
        optionalArgs.add_argument('-v', '--verbosity', action='count', default=0, help=self.verbHelp)
        optionalArgs.add_argument('-m', '--manual', dest='man', action='store_true', default=False, help=self.manHelp)
        optionalArgs.add_argument('-r', '--repeat', type=int, dest='repeat', default=0, help=self.repeathelp, metavar='\b')
        optionalArgs.add_argument('-c', '--camera', type=int, dest='camera', default=0, help=self.cameraHelp, metavar='\b')
        optionalArgs.add_argument('-s', '--sensor', type=int, dest='sensor', default=0, help=self.sensorHelp, metavar='\b')
        optionalArgs.add_argument('-t', dest='times', default=[], nargs='+', help=self.timeHelp, metavar='[\b')
        optionalArgs.add_argument('-d', type=str, dest='days', default=[], nargs='+', help=self.daysHelp, choices=self.daysOfWeek, metavar='[\b')

    def parse(self):
        self.args = self.argParser.parse_args()
        for curTime in self.args.times:
            try:
                datetime.datetime.strptime(curTime, '%H:%M')
            except ValueError:
                raise Error('invalid time format')


class PiFeedFish(object):
    """ Implements the fish feeder which is composed of a server that allows a
        client to change the configuration file, a RabbitMQ server that streams
        the images and sensor readings.
    """
    class Client(object):
        """ Class for the accepted client to the configuration server.
        """
        def __init__(self, verbosity, feeder, conn, addr, port, size, lock):
            """ Class constructor.
            """
            self.verbosity = verbosity
            self.feeder = feeder
            self.conn = conn
            self.addr = addr
            self.port = port
            self.size = size
            self.lock = lock
            self.configFile = 'raspf1.config'

        def run(self):
            """ Waits to accept incoming messages from the client, then writes
                the new feeder configuration to the configuration file.
            """
            # Receive the incoming message.
            try:
                self.config = self.conn.recv(self.size)
                if self.verbosity >= 1:
                    print('%s: Received request from client %s:%s.' % (self.feeder, self.addr, self.port))
            except socket.error as e:
                raise Error(e.strerror)

            # Output the changes being made.
            self.lock.acquire()
            curConfig = self.readConfig()
            self.lock.release()

            newConfig = json.loads(self.config)

            # Make sure to keep the default values in place.
            if newConfig['sensor'] == 0:
                newConfig['sensor'] = curConfig['sensor']
            if newConfig['camera'] == 0:
                newConfig['camera'] = curConfig['camera']
            if not newConfig['manual']:
                newConfig['auto']['times'] = curConfig['auto']['times']
                newConfig['auto']['times'] = curConfig['auto']['days']

            try:
                if self.verbosity >= 1:
                    print('%s: Updating configuration file...' % self.feeder)
                    for key in curConfig.keys():
                        if type(curConfig[key]) is dict:
                            for subkey in curConfig[key].keys():
                                if curConfig[key][subkey] != newConfig[key][subkey]:
                                    print('%s: Updating %s from %s to %s.' % (self.feeder, subkey, curConfig[key][subkey], newConfig[key][subkey]))
                        elif curConfig[key] != newConfig[key]:
                            print('%s: Updating %s from %s to %s.' % (self.feeder, key, curConfig[key], newConfig[key]))
            except ValueError:
                if self.verbosity >= 1:
                    print('%s: Configuration file does not contain a valid JSON object.' % self.feeder)
                if self.verbosity == 2:
                    print('%s: Overwriting configuration file to: %s.' % (self.feeder, self.config))

            # Change the configuration file.
            self.config = newConfig

            self.lock.acquire()
            self.writeConfig()
            self.lock.release()

        def readConfig(self):
            try:
                with open(self.configFile, 'r') as f:
                    curConfig = json.load(f)
                    return curConfig
            except IOError:
                raise Error('cannot write from configuration file')

        def writeConfig(self):
            try:
                with open(self.configFile, 'w+') as f:
                    json.dump(self.config, f)
                if self.verbosity >= 1:
                    print('%s: Successfuly updated configuration file.' % self.feeder)
            except IOError:
                raise Error('cannot write to configuration file')

    class Feeder(threading.Thread):
        """ Class for the feeder.
        """
        def __init__(self, verbosity, feeder, lock):
            threading.Thread.__init__(self)
            self.verbosity = verbosity
            self.feeder = feeder
            self.lock = lock
            self.configFile = 'raspf1.config'

            self.daysOfWeek = {
                'MON': 0,
                'TUE': 1,
                'WED': 2,
                'THU': 3,
                'FRI': 4,
                'SAT': 5,
                'SUN': 6
            }

            # Build a scheduler object that will look at absolute times
            self.scheduler = sched.scheduler(time.time, time.sleep)

        def run(self):
            while True:
                time.sleep(5)

                # Read the configuration file and see what camera value was.
                self.lock.acquire()
                config = self.readConfig()
                self.lock.release()

                # Hardware code for executing the feeders.
                repeat = config['auto']['repeat']
                times = config['auto']['times']
                days = config['auto']['days']

                # Build a list of times.
                dtTimes = []
                for curTime in times:
                    dtTimes.append(datetime.datetime.strptime(curTime, "%H:%M"))

                # Build a list of days.
                dtDays = []
                for day in days:
                    # Change from append to update.
                    dtDays.append(self.daysOfWeek[day])

                # Create a list of datetime objects to be scheduled for the week,
                # where the current day is the reference.
                todayDay = datetime.date.today()
                schedule = []
                for curTime in dtTimes:
                    for curDay in dtDays:
                        if todayDay.weekday() < curDay:
                            daysTill = curDay - todayDay.weekday()
                        else:
                            daysTill = 7 - abs(todayDay.weekday() - curDay)
                        dtDaysTill = datetime.timedelta(days=daysTill)
                        nextSchedDay = todayDay + dtDaysTill
                        nextSchedTime = curTime
                        nextSched = datetime.datetime.combine(nextSchedDay, nextSchedTime.timetz())
                        if self.verbosity >= 1:
                            print('Scheduling a new feed for %s' % str(nextSched))
                        schedule.append(nextSched)

                # Add the schedule to the scheduler.
                for dt in schedule:
                    if dt.date() == todayDay and dt.time() == datetime.datetime.now():
                        # Schedule the feeder.
                        self.feed()

                        # Remove the date
                        dt.remove(dt)

            def feed(self):
                pass

            def readConfig(self):
                try:
                    with open(self.configFile, 'r') as f:
                        curConfig = json.load(f)
                        return curConfig
                except IOError:
                    raise Error('cannot write from configuration file')

    class Camera(threading.Thread):
        """ Class for the camera.
        """
        def __init__(self, verbosity, feeder, event, camera, lock):
            threading.Thread.__init__(self)
            self.verbosity = verbosity
            self.feeder = feeder
            self.event = event
            self.camera = camera
            self.lock = lock
            self.configFile = 'raspf1.config'

        def run(self):
            # Read the configuration file and see what camera value was.
            self.lock.acquire()
            config = self.readConfig()
            if self.camera == 0:
                self.camera = config['camera']
            self.lock.release()
            if self.camera > 0:
                while not self.event.wait(self.camera):
                    self.capture()

        def readConfig(self):
            try:
                with open(self.configFile, 'r') as f:
                    curConfig = json.load(f)
                    return curConfig
            except IOError:
                raise Error('cannot read from configuration file')

        def capture(self):
            if self.verbosity >= 1:
                sys.stdout.write('%s: Capturing new image...\n' % self.feeder)

            # Hardware code for getting an image from the camera goes here.

    class Sensor(threading.Thread):
        """ Class for the temperature sensor.
        """
        def __init__(self, verbosity, feeder, event, sensor, lock):
            threading.Thread.__init__(self)
            self.verbosity = verbosity
            self.feeder = feeder
            self.event = event
            self.sensor = sensor
            self.lock = lock
            self.reading = None
            self.configFile = 'raspf1.config'

        def run(self):
            # Read the configuration file and see what camera value was.
            self.lock.acquire()
            config = self.readConfig()
            if self.sensor == 0:
                self.sensor = config['sensor']
            self.lock.release()

            if self.sensor > 0:
                while not self.event.wait(self.sensor):
                    self.read()

        def readConfig(self):
            try:
                with open(self.configFile, 'r') as f:
                    curConfig = json.load(f)
                    return curConfig
            except IOError:
                raise Error('cannot write to configuration file')

        def read(self):
            if self.verbosity >= 1:
                sys.stdout.write('%s: Reading sensor...\n' % self.feeder)

            # Hardware code for reading from the temperature sensor goes
            # here.

            # Send the sensor reading to the rabbitmq server.

    def __init__(self, verbosity, feeder, man, repeat, times, days, camera,
                 sensor):
        self.verbosity = verbosity
        self.config = {
            'feeder': feeder,      # Feeder to connect to
            'man': man,            # Boolean true if manual feed
            'camera': camera,      # Frames per second of the camera
            'sensor': sensor,      # Number of times to read temp sensor
            'auto': {              # Dictionary for automatic configuration
                'repeat': repeat,  # Number of times to repeat
                'times': times,    # List of times during the day to feed
                'days': days       # List of days to feed
            }
        }
        self.client = None
        self.host = 'localhost'
        self.port = 8080
        self.size = 1024
        self.backlog = 5

    def openSocket(self):
        """ Opens a stream socket.
        """
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(self.backlog)
        except socket.error as e:
            raise ErrorSocketOpen(self.config['feeder'], e.strerror)
        if self.verbosity >= 1:
            print('Starting config server for %s at %s, port %s.' % (self.config['feeder'], self.host, self.port))

    def run(self):
        """ Runs the server.
        """
        # Make sure that a socket is open before running.
        if self.server is None:
            raise Error('')

        # Lock up the config file to the threads.
        lock = threading.Lock()

        # Start the threads that will control the hardware.
        cameraEvent = threading.Event()
        sensorEvent = threading.Event()
        self.camera = self.Camera(self.verbosity, self.config['feeder'], cameraEvent, self.config['camera'], lock)
        self.sensor = self.Sensor(self.verbosity, self.config['feeder'], sensorEvent, self.config['sensor'], lock)
        self.feeder = self.Feeder(self.verbosity, self.config['feeder'], lock)
        self.camera.daemon = True
        self.sensor.daemon = True
        self.feeder.daemon = True
        #self.camera.start()
        #self.sensor.start()
        self.feeder.start()

        # Run until the user quits with CTR-C.
        while True:
            # Try to connect to a client.
            try:
                self.server.listen(self.backlog)
                (clientConn, (clientAddr, clientPort)) = self.server.accept()
            except socket.error as e:
                raise Error(e.strerror)

            if self.verbosity >= 1:
                print('%s: Connected to client %s:%s.' % (self.config['feeder'], clientAddr, clientPort))

            # Process the manual request.
            if self.config['man']:
                if self.verbosity >= 1:
                    print('%s: Processing manual request to start feeding.')
                self.config['man'] = False

            # Process the client.
            newClient = self.Client(self.verbosity, self.config['feeder'], clientConn, clientAddr, clientPort, self.size, lock)
            newClient.run()


def main():
    if DEBUG:
        pdb.set_trace()
    try:
        args = PiFeedFishArgs()
        args.parse()
        args = args.args
    except argparse.ArgumentError as e:
        print(e.strerror)
    except Error as e:
        print(e.msg)
        sys.exit(1)

    try:
        pff = PiFeedFish(args.verbosity, args.feeder, args.man, args.repeat, args.times, args.days, args.camera, args.sensor)
        pff.openSocket()
        pff.run()
    except ErrorSocketOpen as e:
        print(e.msg)
    except ErrorSocketListen as e:
        print(e.msg)
        sys.exit(1)
    except Error as e:
        print(e.msg)
        sys.exit(1)
    except KeyboardInterrupt:
        # No need to close threads here since they are daemons.
        print('\nClosing.')
        sys.exit(1)


if __name__ == "__main__":
    main()
