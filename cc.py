""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
from   os import makedirs as os_makedirs
from   os import path     as os_path
import zlib
import unicodedata
from   urlparse import urlsplit

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




class CC(object):
    paths_cached = dict()


    class Device(object):
        def __init__(self):
            pass


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


        # Returns: []
        def controls(self):
            return self._ensure(self._controls(), [])


        # Returns: []
        def controlledBy(self):
            return self._ensure(self._controlledBy(), [])


        # Returns: []
        def properties(self):
            return self._ensure(self._properties(), [])


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
            return self._ensure(self._artifactNames(), [])



    def __init__(self):
        # all devices; key, Device pairs
        self._devices              = dict()

        self._hashSum              = None

        # cache for device, property dictionary
        self._propDict             = dict()

        # cache for ^() expressions
        # key: (device, expression), value: property
        self._backtrackCache       = dict()

        # list of the path names of downloaded artifacts
        self._downloadedArtifacts  = list()


    @staticmethod
    def sanitizeFilename(filename):
        if isinstance(filename, str):
            filename = filename.decode("utf-8")

        # replace accented characters with the unaccented equivalent
        filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore")

        result = map(lambda x: '_' if x in '<>:"/\|?*' else x, filename)
        return "".join(result)


    @staticmethod
    def urlToDir(url):
        url_comps = urlsplit(url)

        comps = url_comps.netloc + url_comps.path
        comps = comps.split('/')
        # ignore the last component, it is assumed to be a filename
        del comps[-1]

        return os_path.join(*map(lambda sde: CC.sanitizeFilename(sde), comps))


    @staticmethod
    def makedirs(path):
        try:
            os_makedirs(path)
        except OSError:
            if not os_path.isdir(path):
                raise


    @staticmethod
    def saveas(deviceType, filename, directory, CreateDir = True):
        try:
            return CC.paths_cached[deviceType, filename, directory]
        except KeyError:
            dtdir = os_path.join(directory, CC.sanitizeFilename(deviceType))
            if CreateDir:
                CC.makedirs(dtdir)
            path = os_path.normpath(os_path.join(dtdir, CC.sanitizeFilename(filename)))
            CC.paths_cached[deviceType, filename, directory] = path
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
        except UnicodeDecodeError, e:
            return string.encode("utf-8")


    @staticmethod
    def download(url, saveas, verify = True):
        result = requests.get(url, verify = verify)

        if result.status_code != 200:
            raise RuntimeError(result.status_code)

        # 'w' overwrites the file if it exists
        with open(saveas, 'wb') as f:
            map(lambda x: f.write(x), result)

        return saveas


    # Returns: CC.Device
    def device(self, deviceName):
        try:
            return self._devices[deviceName]
        except KeyError:
            return self._device(deviceName)


    # Returns: []
    def controls(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).controls()


    # Returns: []
    def controlledBy(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).controlledBy()


    # Returns: {}
    def properties(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).properties()


    # Returns: {}
    def propertiesDict(self, deviceName, prefixToIgnore = "PLCF#"):
        assert isinstance(deviceName, str)

        if (deviceName, prefixToIgnore) in self._propDict:
            return self._propDict[deviceName, prefixToIgnore]

        result = {}
        for (name, value) in self.properties(deviceName).iteritems():
            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            result[name] = value

        self._propDict[deviceName, prefixToIgnore] = result

        return result


    # Returns: ""
    def getDeviceType(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).deviceType()


    # Returns: ""
    def getDescription(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).description()


    # Returns: []
    def artifacts(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).artifacts()


    # Returns: []
    def getArtefactNames(self, deviceName):
        assert isinstance(deviceName, str)

        return self.device(deviceName).artifactNames()


    # Returns: ""
    def getArtefact(self, deviceType, filename, directory = "."):
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        saveas = self.saveas(deviceType, filename, directory)

        # check if filename has already been downloaded
        if os_path.exists(saveas):
            return saveas

        self._getArtefact(deviceType, filename, saveas)
        self._downloadedArtifacts.append(saveas)

        return saveas


    # Returns: ""
    def getArtefactFromURL(self, url, deviceType, filename, directory = "."):
        assert isinstance(url,        basestring)
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        # ignore deviceType, the URL already makes the path unique
        saveas = self.saveas("", filename, os_path.join(directory, CC.urlToDir(url)))

        # check if filename has already been downloaded
        if os_path.exists(saveas):
            return saveas

        self._getArtefactFromURL(url, filename, saveas)
        self._downloadedArtifacts.append(saveas)

        return saveas


    def getArtefactURL(self, deviceName, name):
        assert isinstance(deviceName, str)
        assert isinstance(name, str)

        artifacts = self.device(deviceName).artifacts()

        if artifacts is None:
            return None

        uris = filter(lambda ua: ua.get("type") == "URI" and ua.get("name") == name, artifacts)
        if len(uris) == 0:
            return None

        assert len(uris) == 1, uris

        return uris[0].get("uri")


    # Returns: []
    def getSimilarDevices(self, deviceName):
        assert isinstance(deviceName, str)

        raise NotImplementedError


    def dump(self, filename, directory = "."):
        assert isinstance(filename, str)

        import zipfile
        if not filename.endswith(".ccdb.zip"):
            filename += ".ccdb.zip"

        filename = os_path.join(directory, self.sanitizeFilename(filename))
        dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)

        dumpfile.writestr(os_path.join("ccdb", "device.dict"), str(self._devices))
        for template in self._downloadedArtifacts:
            dumpfile.write(template, os_path.join("ccdb", template))

        return filename


    def backtrack(self, prop, deviceName):
        assert isinstance(prop,   str)
        assert isinstance(deviceName, str)

        # starting by one device, looking for property X, find a device
        # in a higher level of the hierarchy that has that property

        if (deviceName, prop) in self._backtrackCache:
            return self._backtrackCache[deviceName, prop]

        # starting point: all devices 'device' is controlled by
        leftToProcess = list(self.controlledBy(deviceName))
        processed     = []

        # keep track of number of iterations
        count         = 0

        # process tree in BFS manner
        while True:

            if count > 200:
                print "something went wrong; too many iterations in backtracking while searching for property " + prop
                exit(1)

            if len(leftToProcess) == 0:
                print "error in  backtracking; probably invalid input while searching for property " + prop
                return " ==== BACKTRACKING ERROR ==== "

            elem = leftToProcess.pop()

            if elem in processed:
                continue

            processed.append(elem)

            # get properties of device
            propDict = self.propertiesDict(elem)

            if prop in propDict:
                val = propDict.get(prop)
                self._backtrackCache[deviceName, prop] = val

                return val

            # desired property not found in device x
            else:
                c = self.controlledBy(elem)
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
            crc32 = zlib.crc32(deviceName, crc32)
            if hashobj is not None:
                hashobj.update(deviceName)

            device     = self._devices[deviceName]
            keys       = device.keys()
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
                print "Input error", type(head)
                exit(1)

        return res
