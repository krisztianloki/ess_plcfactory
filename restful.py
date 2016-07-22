# Python libraries
import json
import os
import sys






# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)



import processTemplate     as pt

import glob



# third-party libraries, stored in folder 'libs'
import requests

# disable printing of unsigned SSH connection warnings to console
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# def backtrack(prop, device):
#     assert isinstance(prop,   str)
#     assert isinstance(device, str)
#
#     # starting by one device, looking for property X, determine a device in a higher level
#     # of the hierarchy that has that property
#
#     # FIXME: add to documentation that FIRST fitting value is returned
#
#
#     cached = dict()
#
#
#     # starting point: all devices 'device' is controlled by
#     leftToProcess = controlledByCDDB(device)
#     processed     = []
#
#     # keep track of number of iterations
#     count         = 0
#
#     # process tree in BFS manner
#     while True:
#
#         if count > 200:
#             print "something went wrong; too many iterations in backtracking"
#             exit()
#
#         if len(leftToProcess) == 0:
#             print "error in  backtracking; probably invalid input"
#             return " ==== BACKTRACKING ERROR ==== "
#
#         x = leftToProcess.pop()
#         processed.append(x)
#
# ###########
#         """
#         if x not in cached.keys():
#             # get properties of device
#             propList = propertiesCCDB(x)
#             propDict = pt.createPropertyDict(propList)
#             # add to dict
#             cached[x] = propDict
#
#         else:
#             # retrievce
#             propDict = cached.get(x)
#
#             print "HERE"
#             exit()
#
#         if prop in propDict.keys():
#             val = propDict.get(prop)
#             return val
#
#         # desired property not found in device x
#         else:
#             controlledBy   = controlledByCDDB(x)
#             leftToProcess += controlledBy
#             count         += 1
#
#         """
# ##########
#
#
#
#         # get properties of device
#         propList = propertiesCCDB(x)
#         propDict = pt.createPropertyDict(propList)
#
#         if prop in propDict.keys():
#             val = propDict.get(prop)
#             return val
#
#         # desired property not found in device x
#         else:
#             controlledBy   = controlledByCDDB(x)
#             leftToProcess += controlledBy
#             count         += 1
        


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
    assert isinstance(filename, str)

    #print deviceType, filename
        
    if os.path.exists(filename):
        return

    # FIXME
    # check if filename already exists; if so, simply return




    # alternative URL e.g.
    # https://ics-services.esss.lu.se/ccdb-test/rest/slot/LNS-ISrc-01:Vac-IPC-1/download/PLC_DEVICE_HEADER_TEMPLATE_1.txt

    # https://ccdb.esss.lu.se/rest/slot/LNS-LEBT-010:Vac-VPGCF-001

    # https://ccdb.esss.lu.se/rest/slot/LNS-LEBT-010:Vac-VVM-00081

    # url     = "https://ics-services.esss.lu.se/ccdb-test/rest/deviceType/"  \
    url     = "https://ccdb.esss.lu.se/rest/deviceType/"  \
               + deviceType + "/download/" + filename

    results = requests.get(url, verify=False)

    # 'w' overwrites the file if it exists
    with open(filename, 'wb') as f:
        map(lambda x: f.write(x), results)




def getField(device, field):
    # create URL for GET request
    # url     = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + device

    if device not in glob.deviceDict.keys():

        url     = "https://ccdb.esss.lu.se/rest/slot/" + device
        
        request = requests.get(url, verify=False)
              # False because SSH connection is unsigned
        tmpDict = json.loads(request.text)

        glob.deviceDict[device] = tmpDict


    else:
        tmpDict = glob.deviceDict[device]

    result  = tmpDict.get(field)

    return result
    


# OLD
"""
def getField(device, field):
    # create URL for GET request
    # url     = "https://ics-services.esss.lu.se/ccdb-test/rest/slot/" + device

    url     = "https://ccdb.esss.lu.se/rest/slot/" + device

    request = requests.get(url, verify=False)
              # False because SSH connection is unsigned
    tmpDict = json.loads(request.text)

    result  = tmpDict.get(field)

    return result
"""





# FIXME
"""
memo = dict()

def queryCCDB(plc, field):
    assert isinstance(plc,   str)
    assert isinstance(field, str)

    global memo

    if (plc, field) not in memo.keys():
        result = getField(plc, field)

        # convert from utf-8 to ascii for keys
        result  = map(lambda x: str(x), result)
        
        print "ooo", result
        #exit()
        memo[(plc, field)] = result

    else:
        result = memo.get((plc, field))
        
    #print "..", memo
    #print "oo"
    #exit()

    print memo


    return result 
"""


def queryCCDB(plc, field):
    assert isinstance(plc,   str)
    assert isinstance(field, str)

#    print plc, field
#    print "oo"
#    exit()

    result = getField(plc, field)

    # convert from utf-8 to ascii for keys
    result  = map(lambda x: str(x), result)

    return result


