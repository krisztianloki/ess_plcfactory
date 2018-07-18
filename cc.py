from __future__ import print_function

""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
from   os import path     as os_path
import zlib
try:
    from   urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

try:
    import requests
except ImportError:
    from sys import path as sys_path

    # add directory for third-party libraries to module search path
    parent_dir = os_path.abspath(os_path.dirname(__file__))
    lib_dir    = os_path.join(parent_dir, 'libs')
    sys_path.append(lib_dir)
    del parent_dir
    del lib_dir

    # third-party libraries, stored in folder 'libs'
    import requests


# PLC Factory modules
import helpers



class CC(object):
    TEMPLATE_DIR = "templates"
    paths_cached = dict()


    class Exception(Exception):
        """Base class for Controls and Configuration exceptions"""



    class DownloadException(Exception):
        def __init__(self, url, code):
            super(CC.DownloadException, self).__init__(url, code)
            self.url  = url
            self.code = code


        def __str__(self):
            return "Cannot download {url}: error {code}".format(url  = self.url,
                                                                code = self.code)



    class ArtifactException(DownloadException):
        def __init__(self, dloadexception, deviceName, filename):
            super(CC.ArtifactException, self).__init__(url = dloadexception.url, code = dloadexception.code)
            self.deviceName = deviceName
            self.filename   = filename


        def __str__(self):
            return "Cannot get artifact {art} of {device}: error {code} ({url})".format(device = self.deviceName,
                                                                                        art    = self.filename,
                                                                                        code   = self.code,
                                                                                        url    = self.url)



    class Artifact(object):
        # list of the path names of downloaded artifacts
        downloadedArtifacts = list()

        def __init__(self, device):
            self._device = device


        def __repr__(self):
            return self.name()


        def name(self):
            raise NotImplementedError


        def is_file(self):
            raise NotImplementedError


        def is_uri(self):
            raise NotImplementedError


        def filename(self):
            raise NotImplementedError


        def uri(self):
            raise NotImplementedError


        def uniqueID(self):
            raise NotImplementedError


        # Returns: ""
        def download(self, extra_url = ""):
            # NOTE: we _must not_ use CC.TEMPLATE_DIR here,
            # CCDB_Dump relies on creating an instance variant of TEMPLATE_DIR to point it to its own templates directory
            output_dir = self._device.ccdb.TEMPLATE_DIR

            if self.is_uri():
                filename = CC.urlToFilename(extra_url)
                url      = "/".join([ self.uri(), extra_url ])
                save_as  = CC.saveas(self.uniqueID(), filename, os_path.join(output_dir, CC.urlToDir(url)))
            else:
                filename = self.filename()
                url      = None
                save_as  = CC.saveas(self.uniqueID(), filename, output_dir)

            # check if filename has already been downloaded
            if os_path.exists(save_as):
                return save_as

            try:
                self._download(save_as, url = url)
            except CC.DownloadException as e:
                raise CC.ArtifactException(e, deviceName = self._device.name(), filename = filename)

            self.downloadedArtifacts.append(save_as)

            return save_as



    class Device(object):
        def __init__(self):
            self._inControlledTree = False


        @staticmethod
        def _ensure(var, default):
            #
            # Do not return None
            #
            if var is not None:
                return var

            return default


        # Returns: {}
        def keys(self):
            raise NotImplementedError


        # Returns: ""
        def name(self):
            raise NotImplementedError


        def putInControlledTree(self):
            self._inControlledTree = True


        def isInControlledTree(self):
            return self._inControlledTree


        # Returns: []
        def controls(self):
            return self._ensure(self._controls(), [])


        # Returns: []
        def controlledBy(self, filter_by_controlled_tree = False):
            ctrldBy = self._ensure(self._controlledBy(filter_by_controlled_tree), [])
            if not filter_by_controlled_tree:
                return ctrldBy
            return filter(lambda d: d.isInControlledTree(), ctrldBy)


        # Returns: []
        def properties(self):
            return self._ensure(self._properties(), [])


        # Returns: {}
        def propertiesDict(self, prefixToIgnore = True):
            return self._ensure(self._propertiesDict(), {})


        # Returns: ""
        def deviceType(self):
            return self._ensure(self._deviceType(), "")


        # Returns: ""
        def description(self):
            return self._ensure(self._description(), "")


        # Returns: []
        def artifacts(self):
            return self._ensure(self._artifacts(), [])


        # Returns: []
        def artifactNames(self):
            return map(lambda an: an.name(), filter(lambda fa: fa.is_file(), self.artifacts()))


        # Returns: ""
        def backtrack(self, prop):
            return self._ensure(self._backtrack(prop), "")



    def __init__(self, clear_templates = True):
        # all devices; key, Device pairs
        self._devices              = dict()

        self._hashSum              = None

        # cache for device, property dictionary
        self._propDict             = dict()

        # cache for ^() expressions
        # key: (device, expression), value: property
        self._backtrackCache       = dict()

        if clear_templates:
            # clear templates downloaded in a previous run
            helpers.rmdirs(CC.TEMPLATE_DIR)
        else:
            print("Reusing templates of any previous run")

        helpers.makedirs(CC.TEMPLATE_DIR)


    @staticmethod
    def urlComps(url):
        url_comps = urlsplit(url)

        comps = url_comps.netloc + url_comps.path
        return comps.split('/')


    @staticmethod
    def urlToFilename(url):
        comps = CC.urlComps(url)
        # assume the last component is a filename
        return comps[-1]


    @staticmethod
    def urlToDir(url):
        comps = CC.urlComps(url)

        # ignore the last component, it is assumed to be a filename
        del comps[-1]

        return os_path.join(*map(lambda sde: helpers.sanitizeFilename(sde), comps))


    @staticmethod
    def saveas(uniqueID, filename, directory, CreateDir = True):
        try:
            return CC.paths_cached[uniqueID, filename, directory]
        except KeyError:
            dtdir = os_path.join(directory, helpers.sanitizeFilename(uniqueID))
            if CreateDir:
                helpers.makedirs(dtdir)
            path = os_path.normpath(os_path.join(dtdir, helpers.sanitizeFilename(filename)))
            CC.paths_cached[uniqueID, filename, directory] = path
            return path


    @staticmethod
    def tostring(string):
        if isinstance(string, str) or string is None:
            return string

        if isinstance(string, list):
            return [CC.tostring(s) for s in string]

        if isinstance(string, dict):
            newdict = dict()
            for k in string:
                newdict[CC.tostring(k)] = CC.tostring(string[k])

            return newdict

        assert isinstance(string, unicode), type(string)

        try:
            return string.encode("unicode-escape").decode("string-escape").decode("utf-8").encode("utf-8")
        except UnicodeDecodeError as e:
            return string.encode("utf-8")


    @staticmethod
    def download(url, save_as, verify_ssl_cert = True):
        result = requests.get(url, verify = verify_ssl_cert)

        if result.status_code != 200:
            raise CC.DownloadException(url = url, code = result.status_code)

        # 'w' overwrites the file if it exists
        with open(save_as, 'wb') as f:
            map(lambda x: f.write(x), result)

        return save_as


    # Returns: CC.Device
    def device(self, deviceName, cachedOnly = False):
        try:
            return self._devices[deviceName]
        except KeyError:
            if cachedOnly:
                return None
            return self._device(deviceName)


    # Returns: {}
    def _propertiesDict(self, device, prefixToIgnore = "PLCF#"):
        if prefixToIgnore == True:
            prefixToIgnore = "PLCF#"

        if prefixToIgnore == "":
            return device.properties()

        deviceName = device.name()

        if (deviceName, prefixToIgnore) in self._propDict:
            return self._propDict[deviceName, prefixToIgnore]

        result = {}
        for (name, value) in device.properties().iteritems():
            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            result[name] = value

        self._propDict[deviceName, prefixToIgnore] = result

        return result


    # Returns: []
    def getSimilarDevices(self, deviceName):
        assert isinstance(deviceName, str)

        raise NotImplementedError


    def dump(self, filename, directory = "."):
        assert isinstance(filename, str)

        import zipfile
        if not filename.endswith(".ccdb.zip"):
            filename += ".ccdb.zip"

        filename = os_path.join(directory, helpers.sanitizeFilename(filename))
        dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)

        dumpfile.writestr(os_path.join("ccdb", "device.dict"), str(self._devices))
        for template in self.Artifact.downloadedArtifacts:
            dumpfile.write(template, os_path.join("ccdb", template))

        return filename


    @staticmethod
    def load(filename):
        from ccdb_dump import CCDB_Dump
        print("Trying to load CC dump from", filename)
        return CCDB_Dump.load(filename)


    def _backtrack(self, device, prop):
        assert isinstance(prop,   str)

        deviceName = device.name()

        # starting by one device, looking for property X, find a device
        # in a higher level of the hierarchy that has that property

        if (deviceName, prop) in self._backtrackCache:
            return self._backtrackCache[deviceName, prop]

        # starting point: all devices 'device' is controlled by
        leftToProcess = device.controlledBy(True)
        processed     = []

        # keep track of number of iterations
        count         = 0

        # process tree in BFS manner
        while True:

            if count > 200:
                raise CC.Exception("Something went wrong; too many iterations in backtracking while searching for property " + prop)

            if len(leftToProcess) == 0:
                print("error in  backtracking after {} iterations; probably invalid input while searching for property {}".format(count, prop))
                return " ==== BACKTRACKING ERROR ==== "

            elem = leftToProcess.pop()

            if elem in processed:
                continue

            processed.append(elem)

            # get properties of device
            propDict = elem.propertiesDict()

            if prop in propDict:
                val = propDict.get(prop)
                self._backtrackCache[deviceName, prop] = val

                return val

            # desired property not found in device x
            else:
                c = elem.controlledBy(True)
                if c is not None:
                  leftToProcess = c + leftToProcess
                  count        += 1


    def getHash(self, hashobj = None):
        if self._hashSum is not None:
            return self._hashSum

        if hashobj is not None:
            assert "update" in dir(hashobj) and callable(hashobj.update)

        # compute checksum and hash
        # from all keys and their corresponding values in order, e.g.
        # key_1, value_1, key_2, value_2, ... key_n, value_n
        crc32 = 0

        # get all devices
        deviceNames = self._devices.keys()

        # ... in alphabetical order
        deviceNames.sort()

        # now the same for each device:
        for deviceName in deviceNames:
            device     = self._devices[deviceName]

            # Make sure that only controlled devices are hashed
            if not device.isInControlledTree():
                continue

            crc32 = zlib.crc32(deviceName, crc32)
            if hashobj is not None:
                hashobj.update(deviceName)

            keys = device.keys()
            keys.sort()

            for k in keys:
                tmp = self._getOrderedString([device[k]])

                crc32 = zlib.crc32(k, crc32)
                crc32 = zlib.crc32(tmp, crc32)

                if hashobj is not None:
                    hashobj.update(k)
                    hashobj.update(tmp)

        if hashobj is not None:
            crc32 = zlib.crc32(hashobj.hexdigest())

        self._hashSum = str(crc32)

        return self._hashSum


    # recursively process input in order to create an "ordered"
    # string of all properties
    @staticmethod
    def _getOrderedString(inp):
        assert isinstance(inp, list)

        res       = ""
        toProcess = list(inp)

        while not toProcess == []:

            head = toProcess.pop(0)

            if isinstance(head, basestring):
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
                raise CC.Exception("Input error", type(head))

        return res
