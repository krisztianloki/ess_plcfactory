""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import os
import zlib
import unicodedata



class CC(object):
    def __init__(self):
        self._hashSum        = None

        # all devices and their properties
        # key: device, value: dict of all properties/values
        self._deviceDict     = dict()

        # cache for ^() expressions
        # key: (device, expression), value: property
        self._backtrackCache = dict()

        # list of the path names of downloaded artifacts
        self._artifacts      = list()


    @staticmethod
    def sanitizeFilename(filename):
        if isinstance(filename, str):
            filename = filename.decode("utf-8")

        # replace accented characters with the unaccented equivalent
        filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore")

        result = map(lambda x: '_' if x in '<>:"/\|?*' else x, filename)
        return "".join(result)


    @staticmethod
    def saveas(deviceType, filename, directory):
        return os.path.join(directory, CC.sanitizeFilename(deviceType + "___" + filename))


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


    # Returns: []
    def controls(self, device):
        assert isinstance(device, str)

        raise NotImplementedError


    # Returns: []
    def controlledBy(self, device):
        assert isinstance(device, str)

        raise NotImplementedError


    # Returns: []
    def properties(self, device):
        assert isinstance(device, str)

        raise NotImplementedError


    # Returns: {}
    def propertiesDict(self, device):
        assert isinstance(device, str)

        raise NotImplementedError


    # Returns: ""
    def getDeviceType(self, device):
        assert isinstance(device, str), type(device)

        raise NotImplementedError


    # Returns: ""
    def getDescription(self, device):
        assert isinstance(device, str), type(device)

        raise NotImplementedError


    # Returns: []
    def getArtefactNames(self, device):
        assert isinstance(device, str), type(device)

        raise NotImplementedError


    # Returns: ""
    def getArtefact(self, deviceType, filename, directory = "."):
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        raise NotImplementedError


    # Returns: []
    def getSimilarDevices(self, device):
        assert isinstance(device, str)

        raise NotImplementedError


    def dump(self, filename, directory = "."):
        assert isinstance(filename, str)

        import zipfile
        if not filename.endswith(".ccdb.zip"):
            filename += ".ccdb.zip"

        filename = os.path.join(directory, self.sanitizeFilename(filename))
        dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)

        dumpfile.writestr("ccdb.dump", str(self._deviceDict))
        for template in self._artifacts:
            dumpfile.write(template)

        return filename


    def backtrack(self, prop, device):
        assert isinstance(prop,   str)
        assert isinstance(device, str)

        # starting by one device, looking for property X, find a device
        # in a higher level of the hierarchy that has that property

        if (device, prop) in self._backtrackCache:
            return self._backtrackCache[device, prop]

        # starting point: all devices 'device' is controlled by
        leftToProcess = list(self.controlledBy(device))
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
                self._backtrackCache[device, prop] = val

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
        devices = self._deviceDict.keys()

        # ... in alphabetical order
        devices.sort()

        # now the same for each device:
        for device in devices:
            crc32 = zlib.crc32(device, crc32)
            if hashobj is not None:
                hashobj.update(device)

            properties = self._deviceDict[device]
            keys       = properties.keys()
            keys.sort()

            for k in keys:
                tmp = self._getOrderedString([properties[k]])

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
