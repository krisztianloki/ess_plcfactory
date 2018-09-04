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

try:
    import requests
except ImportError:
    # add directory for third-party libraries to module search path
    parent_dir = os.path.abspath(os.path.dirname(__file__))
    lib_dir    = os.path.join(parent_dir, 'libs')
    sys.path.append(lib_dir)
    del parent_dir
    del lib_dir

    # third-party libraries, stored in folder 'libs'
    import requests


# disable printing of unsigned SSH connection warnings to console
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)



class CCDB(CC):
    class Artifact(CC.Artifact):
        def __init__(self, device, artifact):
            super(CCDB.Artifact, self).__init__(device)
            self._artifact = artifact


        def name(self):
            return self._artifact["name"]


        def is_file(self):
            return self._type() == "FILE"


        def is_uri(self):
            return self._type() == "URI"


        def filename(self):
            return self.name()


        def uri(self):
            return self._artifact["uri"]


        def is_perdevtype(self):
            return self._artifact["kind"] == "TYPE"


        def _download(self, save_as):
            if self.is_perdevtype():
                url = "/".join([ "deviceTypes", self._device.deviceType(), "download", self.filename() ])
            else:
                url = "/".join([ "slot", self._device.name(), "download", self.filename() ])

            return self._device.ccdb.download_from_ccdb(url, save_as)


        def _type(self):
            return self._artifact["type"]



    class Device(CC.Device):
        ccdb = None

        def __init__(self, slot):
            super(CCDB.Device, self).__init__()
            self._slot  = slot
            self._props = None
            self._arts  = None


        def __str__(self):
            return self.name()


        def __repr__(self):
            return str(self._slot)


        def __getitem__(self, item):
            return self._slot[item]


        def keys(self):
            return self._slot.keys()


        def name(self):
            return self._slot["name"]


        def _controls(self):
            return map(lambda dn: self.ccdb.device(dn), self._ensure(self._slot.get("controls", []), []))


        def _controlledBy(self, filter_by_controlled_tree):
            return filter(lambda nn: nn is not None, map(lambda dn: self.ccdb.device(dn, filter_by_controlled_tree), self._ensure(self._slot.get("controlledBy", []), [])))


        def _properties(self):
            if self._props is not None:
                return self._props

            props = self._slot.get("properties", [])
            self._props = dict()
            for prop in props:
                name  = prop.get("name")
                value = prop.get("value")

                if value == "null" and "List" in prop.get("dataType"):
                    value = []

                # sanity check against duplicate values, which would point to an
                # issue with the entered data
                assert name not in self._props

                self._props[name] = value

            return self._props


        def _propertiesDict(self, prefixToIgnore = True):
            return self.ccdb._propertiesDict(self, prefixToIgnore)


        def _deviceType(self):
            return self._slot.get("deviceType", None)


        def _description(self):
            return self._slot.get("description", "")


        def _artifacts(self):
            if self._arts is not None:
                return self._arts

            self._arts = map(lambda a: CCDB.Artifact(self, a), self._ensure(self._slot.get("artifacts", []), []))

            return self._arts


        def _backtrack(self, prop):
            return self.ccdb._backtrack(self, prop)



    def __init__(self, url = None, verify = True):
        CC.__init__(self)
        CCDB.Device.ccdb = self

        if url is None:
            self._url = "https://ccdb.esss.lu.se/rest/"
        else:
            self._url = url

        self._verify = verify


    # download artifact and save as saveas
    def _getArtifact(self, deviceType, filename, saveas):
        url    = self._url + "deviceTypes/" + deviceType + "/download/" + filename

        try:
            return self.download(url, saveas)
        except RuntimeError, e:
            print """ERROR:
Cannot get artifact {dtyp}.{art}: error {code} ({url})""".format(dtyp = deviceType,
                                                                 art  = filename,
                                                                 code = e,
                                                                 url  = url)
            exit(1)


    def _getArtifactFromURL(self, url, filename, saveas):
        return self.download(url, saveas)


    def download_from_ccdb(self, url, saveas):
        return CC.download(self._url + url, saveas, verify = self._verify)


    def download(self, url, saveas):
        return CC.download(url, saveas, verify = self._verify)


    def getSimilarDevices(self, deviceName):
        assert isinstance(deviceName, str)
        assert deviceName.count(":") == 1, "bad formatting of device name: " + deviceName

        slot = deviceName.split(":")[0]

        url = self._url + "slotNames/"

        result  = self._get(url)
        tmpList = filter(lambda x: x["slotType"] == "SLOT", json.loads(result.text)["names"])

        # get all devices in CCDB
        allDevices = map(lambda x: x["name"], tmpList)

        # convert unicode to String
        allDevices = map(lambda x: str(x), allDevices)

        # keep only device
        candidates = filter(lambda x: x.startswith(slot), allDevices)

        # compute Levenshtein distances
        distances  =  map(lambda x: (levenshtein.distance(deviceName, x), x), candidates)
        distances.sort()

        return distances


    def _device(self, deviceName):
        assert isinstance(deviceName, str)
    
        if deviceName not in self._devices:
            url     = self._url + "slots/" + deviceName

            result = self._get(url)

            if result.status_code == 204:
                print "ERROR:"
                print "Device " + deviceName + " not found.\n"
                print "Please check the list of devices in CCDB, and keep"
                print "in mind that device names are case-sensitive.\n"
                print "Maybe you meant one of the following devices: "
                print "(Accesing CCDB, may take a few seconds.)\n"
                print "Most similar device names in CCDB in chosen slot (max. 10):"
                top10 = self.getSimilarDevices(deviceName)[:10]

                if top10 == []:
                    print "No devices found."
                else:
                    for (score, dev) in top10:
                        print dev

                print "\nExiting.\n"
                exit(1)
            elif result.status_code != 200:
                print "ERROR:"
                print "Server returned status code {code}".format(code = result.status_code)
                print "\nExiting.\n"

                exit(1)

            tmpDict = self.tostring(json.loads(result.text))

            if not self._devices:
                # If this is the first device, assume this is the root device, so
                # Greedily request transitive controls information
                url    = "".join([ self._url, "slots/", deviceName, "/controls/?transitive=", str(True) ])

                result = self._get(url)
                if result.status_code == 200:
                    slots = self.tostring(json.loads(result.text)["installationSlots"])
                    for slot in slots:
                        self._devices[slot["name"]] = self.Device(slot)

            # save downloaded data
            self._devices[deviceName] = self.Device(tmpDict)

        return self._devices[deviceName]


    def _get(self, url):
        return requests.get(url, headers = { 'Accept' : 'application/json' }, verify = self._verify)




class CCDB_TEST(CCDB):
    def __init__(self):
        CCDB.__init__(self, "https://ics-services.esss.lu.se/ccdb-test/rest/", verify = False)
