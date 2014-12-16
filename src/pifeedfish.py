#!/usr/bin/env python2.7

""" jskfjlsj
"""

__author__ = 'Igor Janjic, Danny Duangphachanh, Daniel Friedman'
__version__ = '0.1'

import cat
import infoServer

import argparse
import datetime
import json
import sched
import shutil
import subprocess
import socket
import sys
import time
import threading

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


class Feeder(threading.Thread):
    """ Class for the feeder.
    """
    def __init__(self, verbosity, feederName, lockConfig):
        threading.Thread.__init__(self)
        self.verbosity = verbosity
        self.feederName = feederName
        self.lockConfig = lockConfig
        self.configFile = feederName + '.config'
        self.cat = cat.Cat()

        self.daysOfWeek = {
            'MON': 0,
            'TUE': 1,
            'WED': 2,
            'THU': 3,
            'FRI': 4,
            'SAT': 5,
            'SUN': 6
        }
        self.weekOfDays = {
            0: 'MON',
            1: 'TUE',
            2: 'WED',
            3: 'THU',
            4: 'FRI',
            5: 'SAT',
            6: 'SUN'
        }

        # Build a scheduler object that will look at absolute times
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def run(self):
        self.sched = []
        startDay = datetime.date.today()
        startTime = datetime.datetime.now()

        # Read the configuration file and see what camera value was.
        time.sleep(1)  # Let the command line arguments be written first
        self.lockConfig.acquire()
        newConfig = self.readConfig()
        self.lockConfig.release()

        config = None
        while True:

            # Only create a new schedule when the configuration file changes.
            if config != newConfig:
                time.sleep(1)

                config = newConfig
                # Hardware code for executing the feeders.
                curTimes = config['auto']['times']
                curDays = config['auto']['days']

                # Build a list of times.
                dtTimes = []
                for curTime in curTimes:
                    dtTimes.append(datetime.datetime.strptime(curTime, "%H:%M"))

                # Build a list of days.
                dtDays = []
                for curDay in curDays:
                    dtDays.append(self.daysOfWeek[curDay])

                # Create a list of datetime objects to be scheduled for the week,
                # where the current day is the reference.
                self.newSched = []
                for curTime in dtTimes:
                    for curDay in dtDays:
                        if startDay.weekday() < curDay:
                            daysTill = curDay - startDay.weekday()
                        elif startDay.weekday() == curDay:
                            if curTime.time() < startTime.time():
                                daysTill = 7 - abs(startDay.weekday() - curDay)
                            else:
                                daysTill = 0
                        else:
                            daysTill = 7 - abs(startDay.weekday() - curDay)
                        dtDaysTill = datetime.timedelta(days=daysTill)
                        nextSchedDay = startDay + dtDaysTill
                        nextSchedTime = curTime
                        nextSched = datetime.datetime.combine(nextSchedDay, nextSchedTime.timetz())
                        self.newSched.append(nextSched)

                # Add the schedule to the scheduler.
                self.updateSched()

            self.lockConfig.acquire()
            newConfig = self.readConfig()
            self.lockConfig.release()

            # Execute the schedules
            for dt in self.sched:
                if dt.date() == datetime.date.today() and (datetime.datetime.now() - dt) > datetime.timedelta(seconds=2):
                    # Execute the feeder.
                    self.feedNow()

                    # Replace the date with one 7 days from now.
                    self.newSched.append(dt + datetime.timedelta(days=+7))
                    self.newSched.remove(dt)
                    self.updateSched()

    def feedNow(self):
        if self.verbosity >= 1:
            print('%s: Executing feeding...' % self.feederName)
        self.cat.feed(0.5)
        self.cat.water(4)

    def readConfig(self):
        try:
            with open(self.configFile, 'r') as f:
                curConfig = json.load(f)
                return curConfig
        except IOError:
            raise Error('cannot write from configuration file')

    def updateSched(self):
        # For each new entry and missing entry in newSeched, update the
        # schedule.
        for dt in self.sched:
            if dt not in self.newSched:
                if self.verbosity >= 1:
                    print('%s: Removing feed %s from schedule.' % (self.feederName, str(dt)))
                self.sched.remove(dt)

        for dt in self.newSched:
            if dt not in self.sched:
                if self.verbosity >= 1:
                    print('%s: Adding new feed %s to schedule.' % (self.feederName, str(dt)))
                self.sched.append(dt)


class Camera(threading.Thread):
    """ Class for the camera.
    """
    def __init__(self, verbosity, feederName, event, lockConfig, lockCamera):
        threading.Thread.__init__(self)
        self.verbosity = verbosity
        self.feederName = feederName
        self.event = event
        self.lockConfig = lockConfig
        self.lockCamera = lockCamera
        self.configFile = self.feederName + '.config'

    def run(self):
        # Read the configuration file and see what camera value was.
        self.lockConfig.acquire()
        config = self.readConfig()
        self.lockConfig.release()
        fps = config['camera']
        if fps > 0:
            while not self.event.wait(fps):
                self.capture()

    def readConfig(self):
        try:
            with open(self.configFile, 'r') as f:
                curConfig = json.load(f)
                return curConfig
        except IOError:
            raise Error('cannot read from configuration file')

    def capture(self):
        if self.verbosity >= 2:
            sys.stdout.write('%s: Capturing new image...\n' % self.feederName)

        # Capture the image.
        imgName = 'FishTemp.jpg'

        # 640 x 360
        cmdStr = 'raspistill -w 640 -h 360 -o {0}'.format(imgName)

        # Write the temp image.
        subprocess.call(cmdStr.split())

        # Write the actual image.
        self.lockCamera.acquire()
        shutil.copyfile('FishTemp.jpg', 'Fish.jpg')
        self.lockCamera.release()


class Sensor(threading.Thread):
    """ Class for the temperature sensor.
    """
    def __init__(self, verbosity, feederName, event, lockConfig, lockSensor):
        threading.Thread.__init__(self)
        self.verbosity = verbosity
        self.feederName = feederName
        self.event = event
        self.lockConfig = lockConfig
        self.lockSensor = lockSensor
        self.reading = None
        self.configFile = feederName + '.config'

    def run(self):
        # Read the configuration file and see what camera value was.
        self.lockConfig.acquire()
        config = self.readConfig()
        self.lockConfig.release()

        rps = config['sensor']

        if rps > 0:
            while not self.event.wait(rps):
                self.read()

    def readConfig(self):
        try:
            with open(self.configFile, 'r') as f:
                curConfig = json.load(f)
                return curConfig
        except IOError:
            raise Error('cannot write to configuration file')

    def read(self):
        if self.verbosity >= 2:
            sys.stdout.write('%s: Reading sensor...\n' % self.feederName)

        # Hardware code for reading from the temperature sensor goes
        # here.

        # Send the sensor reading to the rabbitmq server.


class Client(threading.Thread):
    """ Class for the accepted client to the configuration server.
    """
    def __init__(self, verbosity, feederName, config, conn, addr, port, size, lockConfig):
        """ Class constructor.
        """
        self.verbosity = verbosity
        self.feederName = feederName
        self.config = config
        self.conn = conn
        self.addr = addr
        self.port = port
        self.size = size
        self.lockConfig = lockConfig
        self.configFile = self.feederName + '.config'

    def run(self):
        """ Waits to accept incoming messages from the client, then writes
            the new feeder configuration to the configuration file.
        """
        try:
            rcvdConfig = self.conn.recv(self.size)
            if self.verbosity >= 1:
                print('%s: Received request from client %s:%s.' % (self.feederName, self.addr, self.port))
        except socket.error as e:
            raise Error(e.strerror)
        self.lockConfig.acquire()
        self.config.newConfig = json.loads(rcvdConfig)
        self.config.updateConfig()
        self.lockConfig.release()

        # Send the sensor info.
        # self.sendSensor(self.conn)

        # Send the camera info.
        # self.sendCamera(self.conn)

    def sendCamera(self, clientConn):
        pass
        # if clientConn:
        #     pdb.set_trace()
        #     filename = 'Fish.jpg'
        #     img = open(filename, 'rb')
        #     clientConn.send('camera')
        #     rcvAck = clientConn.recv(1024)

        #     # if rcvAck != 'ACK':
        #     #     raise Error('')

        #     data = img.read()
        #     img.close()

        #     clientConn.send(data)
        #     rcvAck = clientConn.recv(1024)
        #     print("%s: Pi camera image sent successfully." % self.feederName)

    def sendSensor(self, clientConn):
        pass
        # if clientConn:
        #     filename = 'sensor.txt'
        #     f = open(filename, 'rb')
        #     clientConn.send('sensor')

        #     data = f.read()
        #     f.close()

        #     clientConn.send(data)
        #     print("%s: Sensor reading sent successfully." % self.feederName)


class Config(object):
    def __init__(self, verbosity, feederName, man, times, days, camera, sensor):
        self.verbosity = verbosity
        self.feederName = feederName
        self.config = None
        self.newConfig = {
            'feeder': feederName,      # Feeder to connect to
            'man': man,            # Boolean true if manual feed
            'camera': camera,      # Frames per second of the camera
            'sensor': sensor,      # Number of times to read temp sensor
            'auto': {              # Dictionary for automatic configuration
                'times': times,    # List of times during the day to feed
                'days': days       # List of days to feed
            }
        }
        self.configFile = feederName + '.config'

    def readConfig(self):
        try:
            with open(self.configFile, 'r') as f:
                if self.verbosity >= 1:
                    print('%s: Successfuly read configuration file.' % self.feederName)
                self.config = json.load(f)
        except IOError:
            raise Error('cannot read from configuration file')

    def writeConfig(self):
        try:
            with open(self.configFile, 'w+') as f:
                json.dump(self.config, f)
            if self.verbosity >= 1:
                print('%s: Successfuly updated configuration file.' % self.feederName)
        except IOError:
            raise Error('cannot write to configuration file')

    def processMan(self):
        # Process the manual request.
        if self.config['man']:
            if self.verbosity >= 1:
                print('%s: Processing manual request to start feeding.')
            self.config['man'] = False

            # Add the day and time one minute from now to the configuration.
            manTime = datetime.datetime.now() + datetime.timedelta(minutes=5)
            manTime = manTime.strftime("%H:%M")
            manDay = datetime.date.today().weekday()
            manDay = self.feeder.weekOfDays[manDay]

            self.newConfig['auto']['days'].append(manDay)
            self.newConfig['auto']['times'].append(manTime)
        self.updateConfig()

    def updateConfig(self):
        """ Updates the configuration file.
        """
        # Make sure to keep the default values in place.
        if self.newConfig['sensor'] == 0:
            self.newConfig['sensor'] = self.config['sensor']
        if self.newConfig['camera'] == 0:
            self.newConfig['camera'] = self.config['camera']
        if not self.newConfig['auto']['times']:
            self.newConfig['auto']['times'] = self.config['auto']['times']
        if not self.newConfig['auto']['days']:
            self.newConfig['auto']['days'] = self.config['auto']['days']

        # Show the changes.
        if self.verbosity >= 1:
            print('%s: Updating configuration file...' % self.feederName)
            try:
                for key in self.config.keys():
                    if type(self.config[key]) is dict:
                        for subkey in self.config[key].keys():
                            if self.config[key][subkey] != self.newConfig[key][subkey]:
                                print('%s: Updating %s from %s to %s.' % (self.feederName, subkey, self.config[key][subkey], self.newConfig[key][subkey]))
                    elif self.config[key] != self.newConfig[key]:
                        print('%s: Updating %s from %s to %s.' % (self.feederName, key, self.config[key], self.newConfig[key]))
            except ValueError:
                if self.verbosity >= 1:
                    print('%s: Configuration file does not contain a valid JSON object.' % self.feederName)
                if self.verbosity == 2:
                    print('%s: Overwriting configuration file to: %s.' % (self.feederName, self.config))

        # Change the configuration file.
        self.config = self.newConfig
        self.writeConfig()


class PiFeedFish(object):
    """ Implements the fish feeder which is composed of a server that allows a
        client to change the configuration file.
    """
    def __init__(self, verbosity, ip, port, feederName, man, times, days, camera, sensor):
        self.verbosity = verbosity
        self.feederName = feederName
        self.config = Config(verbosity, feederName, man, times, days, camera, sensor)
        self.clientList = []
        self.host = ip
        self.port = port
        self.size = 1024
        self.backlog = 5
        self.configFile = feederName + '.config'
        self.infoServer = InfoServer

    def openSocket(self):
        """ Opens a stream socket.
        """
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(self.backlog)
        except socket.error as e:
            raise ErrorSocketOpen(self.feederName, e.strerror)
        if self.verbosity >= 1:
            print('Starting config server for %s at %s, port %s.' % (self.feederName, self.host, self.port))

    def run(self):
        """ Runs the server.
        """
        # Make sure that a socket is open before running.
        if self.server is None:
            raise Error('')

        # Lock up the config file to the threads.
        self.lockConfig = threading.Lock()
        self.lockCamera = threading.Lock()
        self.lockSensor = threading.Lock()

        # Start the threads that will control the hardware.
        cameraEvent = threading.Event()
        sensorEvent = threading.Event()
        self.camera = Camera(self.verbosity, self.feederName, cameraEvent, self.lockConfig, self.lockCamera)
        self.sensor = Sensor(self.verbosity, self.feederName, sensorEvent, self.lockConfig, self.lockSensor)
        self.feeder = Feeder(self.verbosity, self.feederName, self.lockConfig)
        self.camera.daemon = True
        self.sensor.daemon = True
        self.feeder.daemon = True
        self.camera.start()
        self.sensor.start()
        self.feeder.start()

        # Run the info server.
        self.infoServer.daemon = True
        self.infoServer.start()

        self.lockConfig.acquire()

        # Get the current configuration.
        self.config.readConfig()

        # Process manual request.
        self.config.processMan()

        self.lockConfig.release()

        # Run until the user quits with CTR-C.
        while True:
            # Try to connect to a client.
            try:
                self.server.listen(self.backlog)
                (clientConn, (clientAddr, clientPort)) = self.server.accept()
            except socket.error as e:
                raise Error(e.strerror)

            # Update the configuration file.
            if self.verbosity >= 1:
                print('%s: Connected to client %s:%s.' % (self.feederName, clientAddr, clientPort))

            self.lockConfig.acquire()
            self.config.readConfig()
            self.lockConfig.release()

            # Give the client its own thread and run it.
            newClient = Client(self.verbosity, self.feederName, self.config, clientConn, clientAddr, clientPort, self.size, self.lockConfig)
            self.clientList.append(newClient)
            newClient.run()


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

        self.daysOfWeek = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN', 'ALL', 'NONE']

        # List of possible fish feeders can be extended for future additions.
        self.possibleFeeders = ['RASPF1']

        # Arguments help.
        self.ipHelp = 'IP address of the server.'
        self.portHelp = 'Port to open for connections.'
        self.feederHelp = 'Feeder to connect to. Allowable choices are ' + ', '.join(self.possibleFeeders) + '.'
        self.helpHelp = 'Show this help message and exit.'
        self.verbHelp = 'Increase output verbosity.'
        self.manHelp = 'Manually start feeding.'
        self.timeHelp = 'A list of times to feed. Allowable choices are from 0:00 to 23:99. Default is 12:00.'
        self.daysHelp = 'A list of days to feed. Allowable choices are ' + ', '.join(self.daysOfWeek) + '. Default is ALL days of the week.'
        self.cameraHelp = 'Frames per second of the camera.'
        self.sensorHelp = 'Number of times to query the temperature sensor per second.'

        # Argparser.
        self.argParser = argparse.ArgumentParser(prog=self.name, description=self.desc, epilog=self.epil, add_help=False)
        requiredArgs = self.argParser.add_argument_group('Required arguments', '')
        optionalArgs = self.argParser.add_argument_group('Optional arguments', '')

        requiredArgs.add_argument('-i', '--ip', type=str, dest='ip', required=True, help=self.ipHelp, metavar='\b')
        requiredArgs.add_argument('-p', '--port', type=int, dest='port', required=True, help=self.portHelp, metavar='\b')
        requiredArgs.add_argument('-f', '--feeder', type=str, dest='feeder', required=True, help=self.feederHelp, choices=self.possibleFeeders,
                                  metavar='\b')
        optionalArgs.add_argument('-h', '--help', action='help', help=self.helpHelp)
        optionalArgs.add_argument('-v', '--verbosity', action='count', default=0, help=self.verbHelp)
        optionalArgs.add_argument('-m', '--manual', dest='man', action='store_true', default=False, help=self.manHelp)
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
        pff = PiFeedFish(args.verbosity, args.ip, args.port, args.feeder, args.man, args.times, args.days, args.camera, args.sensor)
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
