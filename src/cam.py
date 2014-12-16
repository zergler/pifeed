#!/usr/bin/python2.7
import subprocess

img_name = './test.jpg'
cmd_str = 'raspistill -o {0}'.format(img_name)

subprocess.call(cmd_str.split())
