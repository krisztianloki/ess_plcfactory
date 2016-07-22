# Python libraries
import json
import os
import sys

# PLC Factory modules
import processTemplate     as pt
import glob


# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries, stored in folder 'libs'
import requests


# disable printing of unsigned SSH connection warnings to console
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def controlledByCDDB(device):
    assert isinstance(device, str)
    return queryCCDB(device, 'controlBy')


def controlCCDB(plc):
    assert isinstance(plc, str)
    return queryCCDB(plc, 'control')


def propertiesCCDB(plc):
    assert isinstance(plc, str)
    return queryCCDB(plc, 'properties')

def getDeviceType(device):
    assert isinstance(device, str)

    tmp        = getField(device, "deviceType")
    deviceType = tmp.get("name")

    # convert from utf-8 to string
    deviceType = str(deviceType)

    return deviceType


def getArtefactNames(device):
    assert isinstance(device, str)

    # get names of artefacts
    tmp        = getField(device, "deviceType")
    result     = tmp.get("artifacts")
    deviceType = tmp.get("name")

    # convert from utf-8 to string
    deviceType = str(deviceType)

    artefactNames = []
    for elem in result:
        artefactNames.append(str(elem.get("name")))

    return (deviceType, artefactNames)


# download artefact (header/footer), and save in template directory
def getArtefact(deviceType, filename):
    assert isinstance(deviceType, str)
    assert isinstance(filename,   str)

    # check if filename has already been downloaded        
    if os.path.exists(filename):
        return

    # alternative URL e.g.
    # https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-IPC-1/download/PLC_DEVICE_HEADER_TEMPLATE_1.txt
    
    # https://ccdb.esss.lu.se/rest/slot/LNS-LEBT-010:Vac-VVM-00081

    # url     = "https://ics-services.esss.lu.se/ccdb-test/rest/deviceType/"  \
    url     = "https://ccdb.esss.lu.se/rest/deviceType/"  \
               + deviceType + "/download/" + filename

    results = requests.get(url, verify=False)

    # 'w' overwrites the file if it exists
    with open(filename, 'wb') as f:
        map(lambda x: f.write(x), results)


def getField(device, field):
    assert isinstance(device, str)
    assert isinstance(field,  str)

    if device not in glob.deviceDict.keys():

        # create URL for GET request
        url     = "https://ccdb.esss.lu.se/rest/slot/" + device        
        # False because SSH connection is unsigned:        
        request = requests.get(url, verify=False) 
        tmpDict = json.loads(request.text)

        # save downloaded data
        glob.deviceDict[device] = tmpDict

    else:
        
        # retrieve memoized data
        tmpDict = glob.deviceDict[device]

    return tmpDict.get(field)


def queryCCDB(plc, field):
    assert isinstance(plc,   str)
    assert isinstance(field, str)

    result = getField(plc, field)
    # convert from utf-8 to ascii for keys
    result  = map(lambda x: str(x), result)

    return result