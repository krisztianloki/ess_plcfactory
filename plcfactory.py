#!/usr/bin/python
"""
PLC Factory
Gregor Ulm
2016-07-04 to 2016-09-02

See plcfactory.txt for further documentation.
"""

# inbuilt libraries
import json
import os
import sys


# Add vendor directory to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries; cf. folder 'libs' 
import requests

# global variables
numArgs = 2    # note: file name counts as 1 argument

# reading arguments
# TODO typical invocation: 'python plcfactory foo'

args = sys.argv
assert len(args) == numArgs

# get device, e.g. LNS-ISrc-01:Vac-TMPC-1
# https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-TMPC-1
# python plcfactory.py LNS-ISrc-01:Vac-TMPC-1
device = args[1]

# create URL for GET request
url    = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + device
response = requests.get(url, verify=False) # False because SSH connection is unsigned

responseDict = json.loads(response.text)
print responseDict
print "=" * 70


# extract "controls" relationships and properties 

print "Properties:"
properties = responseDict.get('properties')
print properties

print "Controls:"
controls   = responseDict.get('control')
print controls