""" PLC Factory: CCDB dump parser """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import ast
from   os import path as os_path

# PLC Factory modules
from   cc import CC
from ccdb import CCDB


class CCDB_FILE(CC):
    def __init__(self, filename):
        CC.__init__(self)
        CCDB.Device.ccdb = self


        if os_path.isdir(filename):
            self._readdir(filename)
        elif os_path.isfile(filename):
            self._readzip(filename)
        else:
            raise RuntimeError("No CCDB dump found at " + filename)


    def dump(self, filename, dir = None):
        return None


    def _device(self, deviceName):
        raise KeyError("No such device: {}".format(deviceName))


    def _getArtifactFromDir(self, deviceType, filename, directory = None):
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        saveas = self.saveas(deviceType, filename, os_path.join(self._rootpath, "templates"), CreateDir = False)

        # check if filename has already been downloaded
        if os_path.exists(saveas):
            return saveas

        return self._getArtifact(deviceType, filename, None)


    def _getArtifactFromURLFromDir(self, url, deviceType, filename, directory = None):
        assert isinstance(url,        basestring)
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        saveas = self.saveas("", filename, os_path.join(self._rootpath, "templates", CC.urlToDir(url)), CreateDir = False)

        # check if filename has already been downloaded
        if os_path.exists(saveas):
            return saveas

        return self._getArtifactFromURL(url, saveas)


    # extract artifact and save as saveas
    def _getArtifactFromZip(self, deviceType, filename, saveas):
        with self._zipfile.open(self.saveas(deviceType, filename, os_path.join("ccdb", "templates"), CreateDir = False)) as r:
            with open(saveas, "w") as w:
                w.writelines(r)

        return saveas


    # extract artifact and save as saveas
    def _getArtifactFromURLFromZip(self, url, filename, saveas):
        with self._zipfile.open(self.saveas("", filename, os_path.join("ccdb", "templates", CC.urlToDir(url)), CreateDir = False)) as r:
            with open(saveas, "w") as w:
                w.writelines(r)

        return saveas


    def _getArtifact(self, deviceType, filename, saveas):
        raise RuntimeError("Inconsistent CCDB dump: there is no template for {device} with name {filename}".format(device = deviceType, filename = filename))


    # prevent downloading possibly new revisions of def files
    def _getArtifactFromURL(self, url, saveas):
        raise RuntimeError("Inconsistent CCDB dump: there is no template downloaded from URL: {}".format(url))


    # prevent downloading possibly new revisions of def files
    def download(self, url, saveas):
        raise RuntimeError("Inconsistent CCDB dump: there is no template downloaded from URL: {}".format(url))


    def getSimilarDevices(self, device):
        return []


    def _createDevices(self, devicedict):
        deviceDict = ast.literal_eval(devicedict)
        for (key, value) in deviceDict.iteritems():
            self._devices[key] = CCDB.Device(value)


    def _readdir(self, directory):
        if os_path.isdir(os_path.join(directory, "ccdb")):
            self._rootpath = os_path.join(directory, "ccdb")
        else:
            self._rootpath = directory

        try:
            with open(os_path.join(self._rootpath, "device.dict")) as dd:
                devicedict = dd.readline()
        except IOError, e:
            if e.errno == 2:
                raise RuntimeError("Required file 'device.dict' does not exist!")
            else:
                raise

        self._createDevices(devicedict)
        self.getArtifact = self._getArtifactFromDir
        self.getArtifactFromURL = self._getArtifactFromURLFromDir


    def _readzip(self, filename):
        import zipfile
        self._zipfile = zipfile.ZipFile(filename, "r")

        try:
            self._createDevices(self._zipfile.read(os_path.join("ccdb", "device.dict")))
        except KeyError:
            raise RuntimeError("Required file 'device.dict' does not exist!")

        self._getArtifact = self._getArtifactFromZip
        self._getArtifactFromURL = self._getArtifactFromURLFromZip
