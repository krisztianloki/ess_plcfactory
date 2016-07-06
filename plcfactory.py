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


# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries, stored in folder 'libs' 
import requests

# disable printing of unsigned SSH connection warnings to console
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# global variables

# key: deviceID, value: tuple of three lists: properties, controls, controlledBy 
deviceDict = {}
    

# https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-TMPC-1

def queryCCDB(device):

    # create URL for GET request
    url        = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + device
    request    = requests.get(url, verify=False)
                 # False because SSH connection is unsigned
    tmpDict    = json.loads(request.text)
    
    properties = tmpDict.get('properties')
    
    
    controls   = tmpDict.get('control')
    controlBy  = tmpDict.get('controlBy')

    # convert from utf-8 to ascii for keys
    controls   = map(lambda x: str(x), controls)
    controlBy  = map(lambda x: str(x), controlBy)

    return (properties, controls, controlBy)


# exhaustively collect data for all affected devices
def getDevices(remainingDevices):
    global deviceDict
    
    if not remainingDevices:
        return

    device = remainingDevices.pop()
    
    if device not in deviceDict:  # avoid infinite loop
        (prop, contr, contrBy) = queryCCDB(device)
        deviceDict[device]     =  (prop, contr, contrBy)
        return getDevices(remainingDevices + contrBy)
    else:
        return getDevices(remainingDevices)


def writeTemplate():
    pass



if __name__ == "__main__":
    # global variables
    numArgs = 2    # note: file name counts as 1 argument

    # reading arguments
    # typical invocation: 'python plcfactory foo'

    args = sys.argv
    assert len(args) == numArgs, "Illegal number of arguments."

    # get device, e.g. LNS-ISrc-01:Vac-TMPC-1
    # https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-TMPC-1
    # python plcfactory.py LNS-ISrc-01:Vac-TMPC-1
    device = args[1]
    
    (prop, contr, contrBy) = queryCCDB(device)
    
    # adding results to device dictionary
    deviceDict[device]     =  (prop, contr, contrBy)
    
    # recursively gather information about 'controlBy' devices
    # e.g. test with python plcfactory.py LNS-ISrc-01:Vac-TMP-1
    getDevices(contrBy)

    for elem in deviceDict.keys():
        (prop, contr, contrBy) = deviceDict.get(elem)
        print "=" * 60
        print "Device " + elem
        print "Controls:"
        print contr
        print "Controlled by:"
        print contrBy
        print "Properties:"
        print prop
