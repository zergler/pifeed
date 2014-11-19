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

        # Arguments help.
        self.helpHelp = 'Show this help message and exit.'
        self.verbHelp = 'Increase output verbosity.'

        # Argparser.
        argParser = argparse.ArgumentParser(prog=self.name,
                                            description=self.desc,
                                            epilog=self.epil, add_help=False)
        argParser._optionals.title = 'Optional arguments'
        argParser._positionals.title = 'Positional arguments'

        # Optional arguments.
        argParser.add_argument('-h', '--help', action='help',
                               help=self.helpHelp)
        argParser.add_argument('-v', '--verbosity', action='count', default=0,
                               help=self.verbHelp)

        # Required arguments.
        argParser.parse_args()


class PiFeedControl(object):
    """ Implements the PiFeedControl.
    """
    def __init__():
        pass


def main():
    if DEBUG:
        pdb.set_trace()
    args = PiFeedControlArgs()

if __name__ == "__main__":
    main()
