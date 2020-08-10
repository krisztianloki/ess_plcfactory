from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: CCDB Interactions """

__author__     = "Krisztian Loki, Gregor Ulm"
__copyright__  = "Copyright 2016,2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import json
from collections import OrderedDict
from ast import literal_eval as ast_literal_eval

# PLC Factory modules
from   cc import CC



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


        def uniqueID(self):
            if self.is_uri():
                # ignore deviceType, the URL already makes the path unique
                return ""

            if self.is_perdevtype():
                return self._device.deviceType()

            return self._device.name()


        def is_perdevtype(self):
            return self._artifact["kind"] == "TYPE"


        def _download(self, save_as):
            if self.is_file():
                if self.is_perdevtype():
                    url = "/".join([ "deviceTypes", self._device.deviceType(), "download", self.filename() ])
                else:
                    url = "/".join([ "slots", self._device.name(), "download", self.filename() ])

                return self._device.ccdb.download_from_ccdb(url, save_as)
            elif self.is_git():
                # Remove the "filename" part from saveas to get the directory where the repo needs to be cloned into
                cwd = self.saveas()[:-len(self.saveas_filename())-1]
                return self._device.ccdb.git_download(self.saveas_url(), cwd, self.saveas_version())
            else:
                return self._device.ccdb.download(self.saveas_url(), save_as)


        def _type(self):
            return self._artifact["type"]



    class Device(CC.Device):
        def __init__(self, slot, ccdb = None):
            super(CCDB.Device, self).__init__(ccdb)
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
            return map(lambda dn: self.ccdb.device(dn), self._ensure(self._slot.get("controls", []), list))


        def _controlledBy(self, filter_by_controlled_tree):
            return filter(lambda nn: nn is not None, map(lambda dn: self.ccdb.device(dn, filter_by_controlled_tree), self._ensure(self._slot.get("controlledBy", []), list)))


        def _properties(self):
            if self._props is not None:
                return self._props

            props = self._ensure(self._slot.get("properties", []), list, False)
            self._props = OrderedDict()
            for prop in props:
                name  = prop.get("name")
                value = prop.get("value")

                if "List" in prop.get("dataType"):
                    if value == "null":
                        value = []
                    else:
                        value = ast_literal_eval(value)
                        assert isinstance(value, list)

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


        def _artifact(self, a):
            return CCDB.Artifact(self, a)


        def _artifacts(self):
            if self._arts is not None:
                return self._arts

            self._arts = self._ensure(map(lambda a: self._artifact(a), self._ensure(self._slot.get("artifacts", []), list)), list)

            return self._arts


        def _backtrack(self, prop):
            return self.ccdb._backtrack(self, prop)



    def __init__(self, url = None, verify_ssl_cert = True, **kwargs):
        CC.__init__(self, **kwargs)
        CCDB.Device.ccdb = self

        if url is None:
            self._base_url = "https://ccdb.esss.lu.se/rest/"
        else:
            self._base_url = url

        self._verify_ssl_cert = verify_ssl_cert


    def url(self):
        return self._base_url


    def download_from_ccdb(self, url, save_as):
        return CC.download(self._base_url + url, save_as, verify_ssl_cert = self._verify_ssl_cert)


    def download(self, url, save_as):
        return CC.download(url, save_as, verify_ssl_cert = True)


    def getAllDeviceNames(self):
        url = self._base_url + "slotNames/"

        result  = self._get(url)
        tmpList = filter(lambda x: x["slotType"] == "SLOT", json.loads(result.text)["names"])

        # get all devices in CCDB
        allDevices = map(lambda x: x["name"], tmpList)

        # convert unicode to String
        allDevices = map(lambda x: str(x), allDevices)

        return allDevices


    def deviceName(self, deviceName):
        """
            Handles the case when a dictionary from a controls/controlledBy/etc list is used as 'deviceName'
        """
        try:
            return deviceName["name"]
        except TypeError:
            return deviceName


    def _device(self, deviceName):
        deviceName = self.deviceName(deviceName)

        if deviceName not in self._devices:
            url     = self._base_url + "slots/" + deviceName

            result = self._get(url)

            if result.status_code != 200:
                raise CC.DownloadException(url = url, code = result.status_code)

            # Old versions of CCDB returned the installation slot entry itself and not a dictionary
            tmpDict = json.loads(result.text)
            try:
                device = self.tostring(tmpDict["installationSlots"])
                if not device:
                    raise CC.NoSuchDeviceException(deviceName)

                if len(device) > 1:
                    raise CC.Exception("More than one device found with the same name: {}".format(deviceName))

                device = device[0]
            except KeyError:
                device = self.tostring(tmpDict)

            if not self._devices:
                # If this is the first device, assume this is the root device, so
                # Greedily request transitive controls information
                url    = "".join([ self._base_url, "slots/", deviceName, "/controls/?transitive=", str(True) ])

                result = self._get(url)
                if result.status_code == 200:
                    slots = self.tostring(json.loads(result.text)["installationSlots"])
                    for slot in slots:
                        self._devices[slot["name"]] = self.Device(slot, ccdb = self)

            # save downloaded data
            self._devices[deviceName] = self.Device(device, ccdb = self)

        return self._devices[deviceName]


    def _get(self, url):
        return CC.get(url, headers = { 'Accept' : 'application/json' }, verify = self._verify_ssl_cert)




class CCDB_TEST(CCDB):
    def __init__(self, **kwargs):
        kwargs["verify_ssl_cert"] = False
        CCDB.__init__(self, "https://ics-services.esss.lu.se/ccdb-test/rest/", **kwargs)




class CCDB_DEVEL(CCDB):
    def __init__(self, **kwargs):
        kwargs["verify_ssl_cert"] = False
        CCDB.__init__(self, "https://icsvd-app01.esss.lu.se:8443/ccdb-test/rest/", **kwargs)
