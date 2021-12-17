from __future__ import absolute_import

""" PLC Factory: CCDB dump parser """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
import ast
from os import path as os_path

# PLC Factory modules
from cc import CC
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
        class Artifact(CCDB.Artifact):
            def _download(self):
                self._device.ccdb.download(self, self.saveas())


            def downloadExternalLink(self, extension = None, git_tag = None, filetype = "External Link"):
                # Setting git_tag will prevent git operations
                if "full_path" in self._artifact:
                    git_tag = "locally-sourced"
                return super(CCDB_Dump.Dump.Artifact, self).downloadExternalLink(extension, git_tag, filetype)


        class DeviceType(CCDB.DeviceType):
            def url(self):
                return None


        class Device(CCDB.Device):
            def url(self):
                return None


            def type(self):
                return CCDB_Dump.Dump.DeviceType(self.deviceType(), self.ccdb)


            def _artifact(self, a):
                return CCDB_Dump.Dump.Artifact(self, a)


        def __init__(self):
            super(CCDB_Dump.Dump, self).__init__()
            CCDB.Device.ccdb = self


        # do not dump
        def save(self, filename, dir = None):
            return None


        def dump(self, filename, dir = None):
            return self.save(filename, dir)


        # do not clear
        def clear(self):
            pass


        # prevent downloading possibly new revisions of def files
        def download_from_ccdb(self, url, save_as):
            raise CC.DownloadException(url = url, code = "Inconsistent CCDB dump: this artifact was not downloaded from CCDB")


        # prevent downloading possibly new revisions of def files
        def download(self, url, save_as):
            raise CC.DownloadException(url = url, code = "Inconsistent CCDB dump: this artifact was not downloaded")


        def getAllDeviceNames(self):
            return list(self._devices.keys())


        def _createDevices(self, devicedict):
            try:
                deviceDict = ast.literal_eval(devicedict)
            except Exception as e:
                raise CC.Exception(e)

            for (key, value) in deviceDict.items():
                self._devices[key] = self.Device(value, ccdb = self)


        def _device(self, deviceName):
            raise CC.Exception("Inconsistent CCDB dump: No such device: {}".format(deviceName))



    class DirDump(Dump):
        def __init__(self, directory):
            super(CCDB_Dump.DirDump, self).__init__()

            if os_path.isdir(os_path.join(directory, "ccdb")):
                self._rootpath = os_path.join(directory, "ccdb")
            else:
                self._rootpath = directory

            try:
                with open(os_path.join(self._rootpath, CC.DEVICE_DICT)) as dd:
                    devicedict = dd.readline()
            except IOError as e:
                if e.errno == 2:
                    raise CC.Exception("Required file '{}' does not exist!".format(CC.DEVICE_DICT))
                else:
                    raise

            self._createDevices(devicedict)

            # Create our own TEMPLATE_DIR
            self.TEMPLATE_DIR = os_path.join(self._rootpath, CC.TEMPLATE_DIR)


        def url(self):
            return "CCDB Directory at " + self._rootpath



    class ZipDump(Dump):
        def __init__(self, filename):
            super(CCDB_Dump.ZipDump, self).__init__()

            import zipfile
            self._zipfile  = zipfile.ZipFile(filename, "r")
            self._rootpath = "ccdb"
            self._zipfilename = filename

            try:
                self._createDevices(self._zipfile.read(os_path.join(self._rootpath, CC.DEVICE_DICT)).decode())
            except KeyError:
                raise CC.Exception("Required file '{}' does not exist!".format(CC.DEVICE_DICT))


        def url(self):
            return "CCDB Zip file at " + self._zipfilename


        # extract artifact and save as save_as
        def download_from_ccdb(self, url, save_as):
            return self.download(url, save_as)


        # extract artifact and save as save_as
        def download(self, url, save_as):
            try:
                with self._zipfile.open(os_path.join(self._rootpath, save_as)) as r:
                    with open(save_as, "w") as w:
                        try:
                            "".decode()
                            # Python2
                            w.writelines(map(lambda x: x.decode('utf-8').encode('utf-8'), r))
                        except AttributeError:
                            # Python3
                            w.writelines(map(lambda x: x.decode(), r))
            except KeyError as e:
                raise CC.DownloadException(url = url, code = e.args[0])
            except Exception as e:
                raise CC.DownloadException(url = url, code = repr(e))

            return save_as


        # return zipfile
        def save(self, filename, directory = "."):
            if isinstance(filename, str):
                filename = self._save_filename(directory, filename)
                if not filename == self._zipfilename:
                    from shutil import copy
                    copy(self._zipfilename, filename)
                return filename

            return None
