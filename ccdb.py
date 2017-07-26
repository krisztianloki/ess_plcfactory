""" PLC Factory: CCDB Interactions """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import json
import os
import sys
import zlib
import unicodedata

# PLC Factory modules
import plcf_glob as glob
import processTemplate as pt
import levenshtein

# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# URL prefixes for databases
PREFIX_CCDB      = "https://ccdb.esss.lu.se/rest/"
PREFIX_CCDB_TEST = "https://ics-services.esss.lu.se/ccdb-test/rest/"

# third-party libraries, stored in folder 'libs'
import requests


# disable printing of unsigned SSH connection warnings to console
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def controlledBy(device):
    assert isinstance(device, str)
    return query(device, 'controlledBy')


def control(device):
    assert isinstance(device, str)
    res = query(device, 'controls')
    return res


def properties(device):
    assert isinstance(device, str)
    return query(device, 'properties')


def getDeviceType(device):
    assert isinstance(device, str)

    deviceType = getField(device, "deviceType")

    # convert from utf-8 to string
    return str(deviceType)

def getDescription(device):
    assert isinstance(device, str)

    desc = getField(device, "description")

    # convert from utf-8 to string
    return str(desc)

def getArtefactNames(device):
    assert isinstance(device, str)

    artefacts  = getField(device, "artifacts")
    deviceType = getDeviceType(device)

    artefactNames = []
    if artefacts!=None:
      for elem in artefacts:
        artefactNames.append(str(elem.get("name")))

    return (deviceType, artefactNames)


def sanitizeFilename(filename):
    if isinstance(filename, str):
        filename = filename.decode("utf-8")

    # replace accented characters with the unaccented equivalent
    filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore")

    result = map(lambda x: '_' if x in '<>:"/\|?*' else x, filename)
    return "".join(result)


# download artefact (header/footer), and save in template directory
def getArtefact(deviceType, filename):
    assert isinstance(deviceType, str)
    assert isinstance(filename,   str)

    saveas = sanitizeFilename(deviceType + "___" + filename)

    # check if filename has already been downloaded
    if os.path.exists(saveas):
        return saveas

    if glob.production:
        prefix = PREFIX_CCDB
    else:
        prefix = PREFIX_CCDB_TEST

    url     = prefix + "deviceTypes/" + deviceType + "/download/" + filename
    results = requests.get(url, verify=False)

    if results.status_code != 200:
        return None

    # 'w' overwrites the file if it exists
    with open(saveas, 'wb') as f:
        map(lambda x: f.write(x), results)

    return saveas


def getSimilarDevices(device):
    assert isinstance(device, str)
    assert device.count(":") == 1, "bad formatting of device name"

    (slot, deviceName) = device.split(":")

    if glob.production:
        prefix = PREFIX_CCDB
    else:
        prefix = PREFIX_CCDB_TEST

    url = prefix + "slots/"

    # False because SSH connection is unsigned:
    request = requests.get(url, verify=False)
    tmpList = json.loads(request.text)["installationSlots"]

    # get all devices in CCDB
    allDevices = map(lambda x: x["name"], tmpList)

    # convert unicode to String
    allDevices = map(lambda x: str(x), allDevices)

    # keep only device
    candidates = filter(lambda x: x.startswith(slot), allDevices)

    # compute Levenshtein distances
    distances  = \
        map(lambda x: (levenshtein.distance(device, x), x), candidates)
    distances.sort()

    return distances


def getField(device, field):
    assert isinstance(device, str)
    assert isinstance(field,  str)
    
    if device not in glob.deviceDict.keys():
        # create URL for GET request
        if glob.production:
            prefix = PREFIX_CCDB
        else:
            prefix = PREFIX_CCDB_TEST

        url     = prefix + "slots/" + device

        # False because SSH connection is unsigned:
        request = requests.get(url, verify=False)

        if request.status_code == 204:
            print "ERROR:"
            print "Device " + device + " not found.\n"
            print "Please check the list of devices in CCDB, and keep"
            print "in mind that device names are case-sensitive.\n"
            print "Maybe you meant one of the following devices: "
            print "(Accesing CCDB, may take a few seconds.)\n"
            print "Most simlar device names on CCDB in chosen slot (max. 10):"
            top10 = getSimilarDevices(device)[:10]

            if top10 == []:
                print "No devices found."
            else:
                for (score, x) in top10:
                    print x

            print "\nExiting.\n"
            exit()

        tmpDict = json.loads(request.text)

        # save downloaded data
        glob.deviceDict[device] = tmpDict

    else:
        # retrieve memoized data
        tmpDict = glob.deviceDict[device]

    res = tmpDict.get(field, [])
    return res


def query(device, field):
    assert isinstance(device,   str)
    assert isinstance(field, str)

    result = getField(device, field)
    if result != None:
      # convert from utf-8 to ascii for keys
      result  = map(lambda x: str(x), result)

    return result


# let backtrack update a global dictionary
def backtrack(prop, device):
    assert isinstance(prop,   str)
    assert isinstance(device, str)

    # starting by one device, looking for property X, find a device
    # in a higher level of the hierarchy that has that property

    # starting point: all devices 'device' is controlled by
    leftToProcess = controlledBy(device)
    processed     = []

    # keep track of number of iterations
    count         = 0

    # process tree in BFS manner
    while True:

        if count > 200:
            print "something went wrong; too many iterations in backtracking while searching for property " + prop
            exit()

        if len(leftToProcess) == 0:
            print "error in  backtracking; probably invalid input while searching for property " + prop
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
            c = controlledBy(elem)
            if c!=None:
              leftToProcess += controlledBy(elem)
              count         += 1


# recursively process input in order to create an "ordered"
# string of all properties
def getOrderedString(inp):
    assert isinstance(inp, list)

    res       = ""
    toProcess = inp

    while not toProcess == []:

        head = toProcess.pop(0)

        if isinstance(head, unicode):
            res += head

        elif isinstance(head, list):
            for elem in head:
                toProcess.append(elem)

        elif isinstance(head, dict):
            keys = head.keys()
            keys.sort()

            for elem in keys:
                toProcess.append(elem)
                toProcess.append(head[elem])

        elif isinstance(head, bool):
            res += str(head)

        elif head is None:
            continue

        else:
            print "Input error", type(head)
            exit()

    return res


def getHash():

    if not glob.hashSum == None:
        return glob.hashSum

    # compute hash sum
    else:
        crc32 = 0

        # get all devices
        devices = glob.deviceDict.keys()

        # ... in alphabetical order
        devices.sort()

        # now the same for each device:
        for device in devices:
            crc32 = zlib.crc32(device, crc32)

            properties = glob.deviceDict[device]
            keys       = properties.keys()
            keys.sort()

            for k in keys:
                crc32 = zlib.crc32(k, crc32)
                crc32 = zlib.crc32(getOrderedString([properties[k]]), crc32)



        # Now 'tmp' is one string with all keys and their corresponding
        # values in order, e.g.
        # key_1, value_1, key_2, value_2, ... key_n, value_n

        # compute checksum of string
        glob.hashSum = str(crc32)

        return glob.hashSum
