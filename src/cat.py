#!/usr/bin/python2

import RPi.GPIO as GPIO
from servo.Adafruit_PWM_Servo_Driver import PWM
from time import sleep


class Cat:
    def __init__(self):
        self.IA_pin = 7
        self.IB_pin = 8

        # Set numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup pins and turn pump off
        GPIO.setup(self.IA_pin, GPIO.OUT)
        GPIO.setup(self.IB_pin, GPIO.OUT)
        GPIO.output(self.IA_pin, False)
        GPIO.output(self.IB_pin, False)

        # Initialise the PWM device using the default address
        self.pwm = PWM(0x40, debug=False)

        # Set frequency to 60 Hz
        self.pwm.setPWMFreq(60)

    def feed(self, feed_time):
        self.pwm.setPWM(0, 0, 600)
        sleep(feed_time)
        self.pwm.setPWM(0, 0, 200)

    def water(self, pour_time):
        GPIO.output(self.IA_pin, False)
        GPIO.output(self.IB_pin, True)
        sleep(pour_time)
        GPIO.output(self.IA_pin, False)
        GPIO.output(self.IB_pin, False)

def main():
    cat = Cat()
    cat.feed(0.5)
    cat.water(4)

if __name__ == '__main__':
    main()
