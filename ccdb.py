""" PLC Factory: CCDB Interactions """

__author__     = "Krisztian Loki, Gregor Ulm"
__copyright__  = "Copyright 2016,2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import json
import os
import sys

# PLC Factory modules
from   cc import CC
import levenshtein

# add directory for third-party libraries to module search path
parent_dir = os.path.abspath(os.path.dirname(__file__))
lib_dir    = os.path.join(parent_dir, 'libs')
sys.path.append(lib_dir)

# third-party libraries, stored in folder 'libs'
import requests


# disable printing of unsigned SSH connection warnings to console
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)



class CCDB(CC):
    def __init__(self, url = None):
        CC.__init__(self)

        self._propDict = dict()

        if url is None:
            self._url = "https://ccdb.esss.lu.se/rest/"
        else:
            self._url = url


    @staticmethod
    def _ensure(var, default):
        #
        # Do not return None
        #
        if var is not None:
            return var

        return default


    def controls(self, device):
        assert isinstance(device, str)

        return self._ensure(self._getField(device, 'controls'), [])


    def controlledBy(self, device):
        assert isinstance(device, str)

        return self._ensure(self._getField(device, 'controlledBy'), [])


    def properties(self, device):
        assert isinstance(device, str)

        return self._ensure(self._getField(device, 'properties'), [])


    def propertiesDict(self, device, prefixToIgnore = "PLCF#"):
        if (device, prefixToIgnore) in self._propDict:
            return self._propDict[device, prefixToIgnore]

        propList = self.properties(device)
        result = {}

        for elem in propList:
            assert isinstance(elem, dict), type(elem)

            name  = elem.get("name")
            value = elem.get("value")

            if value == "null" and "List" in elem.get("dataType"):
                value = []

            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            # sanity check against duplicate values, which would point to an
            # issue with the entered data
            assert name not in result

            result[name] = value

        self._propDict[device, prefixToIgnore] = result

        return result


    def getDeviceType(self, device):
        assert isinstance(device, str), type(device)

        return self._getField(device, "deviceType")


    def getDescription(self, device):
        assert isinstance(device, str), type(device)

        return self._getField(device, "description")


    def getArtefactNames(self, device):
        assert isinstance(device, str), type(device)

        artefacts  = self._getField(device, "artifacts")

        artefactNames = []
        if artefacts is not None:
          for elem in artefacts:
            artefactNames.append(elem.get("name"))

        return artefactNames


    # download artefact and save in template directory
    def getArtefact(self, deviceType, filename, directory = "."):
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        saveas = self.saveas(deviceType, filename, directory)

        # check if filename has already been downloaded
        if os.path.exists(saveas):
            return saveas

        url    = self._url + "deviceTypes/" + deviceType + "/download/" + filename
        result = self._get(url)

        if result.status_code != 200:
            return None

        # 'w' overwrites the file if it exists
        with open(saveas, 'wb') as f:
            map(lambda x: f.write(x), result)

        self._artifacts.append(saveas)

        return saveas


    def getSimilarDevices(self, device):
        assert isinstance(device, str)
        assert device.count(":") == 1, "bad formatting of device name: " + device

        (slot, deviceName) = device.split(":")

        url = self._url + "slots/"

        # False because SSH connection is unsigned:
        result  = self._get(url)
        tmpList = json.loads(result.text)["installationSlots"]

        # get all devices in CCDB
        allDevices = map(lambda x: x["name"], tmpList)

        # convert unicode to String
        allDevices = map(lambda x: str(x), allDevices)

        # keep only device
        candidates = filter(lambda x: x.startswith(slot), allDevices)

        # compute Levenshtein distances
        distances  =  map(lambda x: (levenshtein.distance(device, x), x), candidates)
        distances.sort()

        return distances


    def _getField(self, device, field):
        assert isinstance(device, str)
        assert isinstance(field,  str)
    
        if device not in self._deviceDict:
            url     = self._url + "slots/" + device

            result = self._get(url)

            if result.status_code == 204:
                print "ERROR:"
                print "Device " + device + " not found.\n"
                print "Please check the list of devices in CCDB, and keep"
                print "in mind that device names are case-sensitive.\n"
                print "Maybe you meant one of the following devices: "
                print "(Accesing CCDB, may take a few seconds.)\n"
                print "Most simlar device names in CCDB in chosen slot (max. 10):"
                top10 = self.getSimilarDevices(device)[:10]

                if top10 == []:
                    print "No devices found."
                else:
                    for (score, dev) in top10:
                        print dev

                print "\nExiting.\n"
                exit()

            tmpDict = self.tostring(json.loads(result.text))

            # save downloaded data
            self._deviceDict[device] = tmpDict

        else:
            # retrieve memoized data
            tmpDict = self._deviceDict[device]

        res = tmpDict.get(field, [])

        return res


    def _get(self, url):
        # False because SSH connection is unsigned:
        return requests.get(url, verify = False)




class CCDB_TEST(CCDB):
    def __init__(self):
        CCDB.__init__(self, "https://ics-services.esss.lu.se/ccdb-test/rest/")
