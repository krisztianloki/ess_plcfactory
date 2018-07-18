from __future__ import absolute_import

""" PLC Factory: Template Processing """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"

# PLC Factory modules
import plcf


def processAll(lines, device):
    assert isinstance(lines,  list)

    propDict = device.propertiesDict()

    # read each line, process them, add one by one to accumulator
    return map(lambda x: plcf.processLine(x, device, propDict), lines)


def getAllLines(filename):
    assert isinstance(filename, str)

    with open(filename) as f:
        lines = f.readlines()

    return lines


def process(device, filename_or_template):
    if isinstance(filename_or_template, list):
        lines = filename_or_template
    else:
        lines = getAllLines(filename_or_template)

    return processAll(lines, device)
