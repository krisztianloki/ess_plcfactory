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


class CCDB_Dump(object):
    @staticmethod
    def load(filename):
        if os_path.isdir(filename):
            return CCDB_Dump.DirDump(filename)
        elif os_path.isfile(filename):
            return CCDB_Dump.ZipDump(filename)
        else:
            raise CC.Exception("No CCDB dump found at " + filename)



    class Dump(CCDB):
        def __init__(self):
            super(CCDB_Dump.Dump, self).__init__()
            CCDB.Device.ccdb = self


        def dump(self, filename, dir = None):
            return None


        # prevent downloading possibly new revisions of def files
        def download_from_ccdb(self, url, save_as):
            raise CC.DownloadException(url = url, code = "Inconsistent CCDB dump: this artifact was not downloaded from CCDB")


        # prevent downloading possibly new revisions of def files
        def download(self, url, save_as):
            raise CC.DownloadException(url = url, code = "Inconsistent CCDB dump: this artifact was not downloaded")


        def getSimilarDevices(self, device):
            return []


        def _createDevices(self, devicedict):
            deviceDict = ast.literal_eval(devicedict)
            for (key, value) in deviceDict.iteritems():
                self._devices[key] = self._create_device(value)


        def _device(self, deviceName):
            raise CC.Exception("Inconsistent CCDB dump: No such device: {}".format(deviceName))



    class DirDump(Dump):
        class Artifact(CCDB.Artifact):
            def download(self, extra_url = "", output_dir = "."):
                return super(CCDB_Dump.DirDump.Artifact, self).download(extra_url, output_dir = os_path.join(self._device.ccdb._rootpath, CC.TEMPLATE_DIR))



        class Device(CCDB.Device):
            def _artifact(self, a):
                return CCDB_Dump.DirDump.Artifact(self, a)



        def __init__(self, directory):
            super(CCDB_Dump.DirDump, self).__init__()

            if os_path.isdir(os_path.join(directory, "ccdb")):
                self._rootpath = os_path.join(directory, "ccdb")
            else:
                self._rootpath = directory

            try:
                with open(os_path.join(self._rootpath, "device.dict")) as dd:
                    devicedict = dd.readline()
            except IOError, e:
                if e.errno == 2:
                    raise CC.Exception("Required file 'device.dict' does not exist!")
                else:
                    raise

            self._createDevices(devicedict)


        def _create_device(self, device):
            return CCDB_Dump.DirDump.Device(device)



    class ZipDump(Dump):
        class Device(CCDB.Device):
            def _artifact(self, a):
                return CCDB.Artifact(self, a)



        def __init__(self, filename):
            super(CCDB_Dump.ZipDump, self).__init__()

            import zipfile
            self._zipfile  = zipfile.ZipFile(filename, "r")
            self._rootpath = "ccdb"

            try:
                self._createDevices(self._zipfile.read(os_path.join(self._rootpath, "device.dict")))
            except KeyError:
                raise CC.Exception("Required file 'device.dict' does not exist!")


        def _create_device(self, device):
            return CCDB_Dump.ZipDump.Device(device)



        # extract artifact and save as save_as
        def download_from_ccdb(self, url, save_as):
            return self.download(url, save_as)


        # extract artifact and save as save_as
        def download(self, url, save_as):
            try:
                with self._zipfile.open(os_path.join(self._rootpath, save_as)) as r:
                    with open(save_as, "w") as w:
                        w.writelines(r)
            except KeyError as e:
                raise CC.DownloadException(url = url, code = e.args[0])
            except Exception as e:
                raise CC.DownloadException(url = url, code = repr(e))

            return save_as
