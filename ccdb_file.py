""" PLC Factory: CCDB dump parser """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import ast
import os
import sys

# PLC Factory modules
from   cc import CC


class CCDB_FILE(CC):
    def __init__(self, filename):
        CC.__init__(self)

        if os.path.isdir(filename):
            self._readdir(filename)
        elif os.path.isfile(filename):
            self._readzip(filename)
        else:
            raise RuntimeError("No CCDB dump found at " + filename)


    def dump(self, filename, dir = None):
        return None


    def _inconsistent(self, device, field):
        raise KeyError("Inconsistent CCDB dump: {device} has no field {field}".format(device = device, field = field))


    def _controls(self, device):
        return self._inconsistent(device, 'controls')


    def _controlledBy(self, device):
        return self._inconsistent(device, 'controlledBy')


    def _properties(self, device):
        return self._inconsistent(device, 'properties')


    def _propertiesDict(self, device, prefixToIgnore):
        return self._inconsistent(device, None)


    def _getDeviceType(self, device):
        return self._inconsistent(device, "deviceType")


    def _getDescription(self, device):
        return self._inconsistent(device, "description")


    def _artefacts(self, device):
        return self._inconsistent(device, "artifacts")


    def _getArtefactFromDir(self, deviceType, filename, directory = None):
        assert isinstance(deviceType, str)
        assert isinstance(filename,   basestring)

        saveas = self.saveas(deviceType, filename, os.path.join(self._rootpath, "templates"), CreateDir = False)

        # check if filename has already been downloaded
        if os.path.exists(saveas):
            return saveas

        return self._getArtefact(deviceType, filename, None)


    # extract artefact and save as saveas
    def _getArtefactFromZip(self, deviceType, filename, saveas):
        with self._zipfile.open(self.saveas(deviceType, filename, os.path.join("ccdb", "templates"), CreateDir = False)) as r:
            with open(saveas, "w") as w:
                w.writelines(r)

        return saveas


    def _getArtefact(self, deviceType, filename, saveas):
        raise RuntimeError("Inconsistent CCDB dump: there is no template for {device} with name {filename}".format(device = deviceType, filename = filename))


    def getSimilarDevices(self, device):
        return []


    def _createDeviceDict(self, devicedict):
        self._deviceDict = ast.literal_eval(devicedict)


    def _readdir(self, directory):
        if os.path.isdir(os.path.join(directory, "ccdb")):
            self._rootpath = os.path.join(directory, "ccdb")
        else:
            self._rootpath = directory

        try:
            with open(os.path.join(self._rootpath, "device.dict")) as dd:
                devicedict = dd.readline()
        except IOError, e:
            if e.errno == 2:
                raise RuntimeError("Required file 'device.dict' does not exist!")
            else:
                raise

        self._createDeviceDict(devicedict)
        self.getArtefact = self._getArtefactFromDir


    def _readzip(self, filename):
        import zipfile
        self._zipfile = zipfile.ZipFile(filename, "r")

        try:
            self._createDeviceDict(self._zipfile.read(os.path.join("ccdb", "device.dict")))
        except KeyError:
            raise RuntimeError("Required file 'device.dict' does not exist!")

        self._getArtefact = self._getArtefactFromZip
