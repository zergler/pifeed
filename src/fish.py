#!/usr/bin/python2

import RPi.GPIO as GPIO
from time import sleep


class Fish:
    def __init__(self):
        self.AIA_pin = 7
        self.AIB_pin = 8
        self.BIA_pin = 9
        self.BIB_pin = 11

        # Set numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup pins and turn pump off
        GPIO.setup(self.AIA_pin, GPIO.OUT)
        GPIO.setup(self.AIB_pin, GPIO.OUT)
        GPIO.setup(self.BIA_pin, GPIO.OUT)
        GPIO.setup(self.BIB_pin, GPIO.OUT)
        GPIO.output(self.AIA_pin, False)
        GPIO.output(self.AIB_pin, False)
        GPIO.output(self.BIA_pin, False)
        GPIO.output(self.BIB_pin, False)

    def feed(self, feed_time):
        GPIO.output(self.AIA_pin, False)
        GPIO.output(self.AIB_pin, True)
        sleep(feed_time)
        GPIO.output(self.AIA_pin, False)
        GPIO.output(self.AIB_pin, False)
        
    def water(self, pour_time):
        GPIO.output(self.BIA_pin, False)
        GPIO.output(self.BIB_pin, True)
        sleep(pour_time)
        GPIO.output(self.BIA_pin, False)
        GPIO.output(self.BIB_pin, False)


def main():
    fish = Fish()
    fish.feed(2)
    fish.water(4)

if __name__ == '__main__':
    main()
