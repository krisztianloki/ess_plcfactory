# Python libraries
import json
import os
import sys

# PLC Factory modules
import glob
import processTemplate as pt



# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries, stored in folder 'libs'
import requests


# disable printing of unsigned SSH connection warnings to console
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def controlledBy(device):
    assert isinstance(device, str)
    return query(device, 'controlBy')


def control(device):
    assert isinstance(device, str)
    return query(device, 'control')


def properties(device):
    assert isinstance(device, str)
    return query(device, 'properties')


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


def query(device, field):
    assert isinstance(device,   str)
    assert isinstance(field, str)

    result = getField(device, field)
    # convert from utf-8 to ascii for keys
    result  = map(lambda x: str(x), result)

    return result
    
    
# let backtrack update a global dictionary
def backtrack(prop, device):
    assert isinstance(prop,   str)
    assert isinstance(device, str)

    # starting by one device, looking for property X, determine a device in a higher level
    # of the hierarchy that has that property

    # FIXME: add to documentation that FIRST fitting value is returned

    # starting point: all devices 'device' is controlled by
    leftToProcess = controlledBy(device)
    processed     = []

    # keep track of number of iterations
    count         = 0

    # process tree in BFS manner
    while True:

        if count > 200:
            print "something went wrong; too many iterations in backtracking"
            exit()

        if len(leftToProcess) == 0:
            print "error in  backtracking; probably invalid input"
            return " ==== BACKTRACKING ERROR ==== "

        elem = leftToProcess.pop()
        processed.append(elem)

        if elem not in glob.cached.keys():
            # get properties of device
            propList = properties(elem)
            propDict = pt.createPropertyDict(propList)
            # add to dict
            glob.cached[elem] = propDict

        else:
            # retrievce cached dictionary
            propDict = glob.cached.get(elem)

        if prop in propDict.keys():
            val = propDict.get(prop)
            return val

        # desired property not found in device x
        else:
            leftToProcess += controlledBy(elem)
            count         += 1
            