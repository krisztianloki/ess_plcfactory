from __future__ import absolute_import
from __future__ import print_function

import filecmp
import os
import shutil
import tempfile
import unittest
import zipfile

import ccdb
import ccdb_dump
from ccdb_factory import CCDB_Factory



class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        if type is None:
            shutil.rmtree(self.dirpath)



class mkstemp(object):
    def __init__(self, **kwargs):
        (self.tmpfile, self.tmpfilepath) = tempfile.mkstemp(**kwargs)


    def __enter__(self):
        return (self.tmpfile, self.tmpfilepath)


    def __exit__(self, type, value, traceback):
        os.unlink(self.tmpfilepath)
#        try:
#            os.close(self.tmpfile)
#        except IOError as e:
#            if e.errno != 9:
#                raise



class TmpDB(object):
    def __init__(self):
        self.factory = CCDB_Factory()
        (self.tmpfile, self.tmpfilepath) = tempfile.mkstemp()


    def __str__(self):
        return self.tmpfilepath


    def __repr__(self):
        return str(self)


    def clear(self):
        os.unlink(self.tmpfilepath)


    def save(self):
        with os.fdopen(self.tmpfile, 'wb') as fo:
            self.factory.save(fo)

        del self.factory



class EmptyDB(TmpDB):
    def __init__(self):
        super(EmptyDB, self).__init__()
        self.save()



class OneDeviceDB(TmpDB):
    def __init__(self):
        super(OneDeviceDB, self).__init__()
        self.factory.addDevice("type", "device")
        self.save()



class MultiDeviceDB(TmpDB):
    num_of_directly_controlled_devices = 3
    controls_list = ["bar1_level1", "bar1_level2", "foo1_level1", "foo2_level1"]
    def __init__(self):
        super(MultiDeviceDB, self).__init__()
        root = self.factory.addDevice("root", "root")
        root.addDevice("foo", "foo1_level1").addDevice("bar", "bar1_level2")
        root.addDevice("bar", "bar1_level1")
        root.addDevice("foo", "foo2_level1")
        self.save()



class ArtifactDB(TmpDB):
    txtext              = ".txt"
    pyext               = ".py"
    artifact            = "artifact"
    artifact_txt        = artifact + txtext
    artifact_py         = artifact + pyext
    device_artifact_txt = "device" + artifact + txtext
    device_artifact_py  = "device" + artifact + ".dpy"
    tag                 = "test"
    test_artifact_txt   = artifact + CCDB_Factory.TAG_SEPARATOR + tag + txtext
    url                 = "https://test.ccdb_dump.ess/artifact/file"
    test_url            = "https://test.ccdb_dump.ess/artifact/test_file"
    foobar              = "foobar"
    epi                 = "EPI"
    test_epi            = epi + CCDB_Factory.TAG_SEPARATOR + tag
    beast               = "BEAST"
    speced_epi          = "BEAST[{}]".format(foobar)
    epi_file            = artifact + ".def"
    test_epi_file       = artifact + CCDB_Factory.TAG_SEPARATOR + tag + ".def"
    spec                = foobar
    speced_epi_file     = foobar + ".alarms"

    def __init__(self, utf = False):
        super(ArtifactDB, self).__init__()

        prefix = "utf_" if utf else ""
        self.artifact_txt        = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.artifact_txt)
        self.artifact_py         = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.artifact_py)
        self.test_artifact_txt   = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.test_artifact_txt)
        self.device_artifact_txt = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.device_artifact_txt)
        self.device_artifact_py  = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.device_artifact_py)
        self.epi_file            = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.epi_file)
        self.test_epi_file       = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.test_epi_file)
        self.speced_epi_file     = os.path.join(tempfile.gettempdir(), prefix + ArtifactDB.speced_epi_file)

        self.artifacts = [ArtifactDB.artifact_py, ArtifactDB.artifact_txt, ArtifactDB.test_artifact_txt, ArtifactDB.device_artifact_txt, ArtifactDB.device_artifact_py]
        self.links     = [ArtifactDB.epi_file, ArtifactDB.test_epi_file, ArtifactDB.speced_epi_file, __file__, __file__]

        if utf:
            with open(__file__) as of:
                with open(self.artifact_txt, "w") as uof:
                    uof.writelines(of)
                    try:
                        # Python 3
                        print("0=close, 1=open1, 2=open2," + u"\u2026", file = uof)
                    except UnicodeEncodeError:
                        # Python 2
                        print("0=close, 1=open1, 2=open2," + u"\u2026".encode('utf-8'), file = uof)
        else:
            shutil.copy(__file__, self.artifact_txt)

        with open(self.artifact_txt) as af:
            with open(self.artifact_py, "w") as paf:
                paf.writelines(map(lambda x: "PY_" + x, af))

        with open(self.artifact_txt) as af:
            with open(self.test_artifact_txt, "w") as taf:
                taf.writelines(map(lambda x: CCDB_Factory.TAG_SEPARATOR + x, af))

        with open(self.artifact_txt) as af:
            with open(self.device_artifact_txt, "w") as daf:
                daf.writelines(map(lambda x: "DEVICE_" + x, af))

        with open(self.artifact_txt) as af:
            with open(self.device_artifact_py, "w") as daf:
                daf.writelines(map(lambda x: "DEVICE_PY_" + x, af))

        with open(self.artifact_txt) as af:
            with open(self.epi_file, "w") as epi:
                epi.writelines(map(lambda x: "EPI_PY_" + x, af))

        with open(self.artifact_txt) as af:
            with open(self.test_epi_file, "w") as epi:
                epi.writelines(map(lambda x: CCDB_Factory.TAG_SEPARATOR + "EPI_PY_" + x, af))

        with open(self.artifact_txt) as af:
            with open(self.speced_epi_file, "w") as epi:
                epi.writelines(map(lambda x: self.foobar + "EPI_PY_" + x, af))

        self.factory.addArtifact("type", ArtifactDB.artifact_py,       self.artifact_py)
        self.factory.addArtifact("type", ArtifactDB.artifact_txt,      self.artifact_txt)
        self.factory.addArtifact("type", ArtifactDB.test_artifact_txt, self.test_artifact_txt)
        self.factory.addLink("type", ArtifactDB.epi, ArtifactDB.url,             self.epi_file)
        self.factory.addLink("type", ArtifactDB.test_epi, ArtifactDB.test_url,   self.test_epi_file)
        self.factory.addLink("type", ArtifactDB.speced_epi, ArtifactDB.test_url, self.speced_epi_file)
        self.factory.addLink("type", "BEAST TREE", ArtifactDB.test_url, __file__)
        self.factory.addLink("type", "BEAST TREE[map]", ArtifactDB.test_url, __file__)
        device = self.factory.addDevice("type", "device")
        device.addArtifact(ArtifactDB.device_artifact_txt, self.device_artifact_txt)
        device.addArtifact(ArtifactDB.device_artifact_py,  self.device_artifact_py)

        self.save()


    def clear(self):
        super(ArtifactDB, self).clear()
        os.unlink(self.artifact_py)
        os.unlink(self.artifact_txt)
        os.unlink(self.test_artifact_txt)
        os.unlink(self.device_artifact_txt)
        os.unlink(self.device_artifact_py)
        os.unlink(self.epi_file)
        os.unlink(self.test_epi_file)
        os.unlink(self.speced_epi_file)



class TestCCDBDump(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.EMPTY_ZIP        = EmptyDB()
        cls.ONE_DEVICE_ZIP   = OneDeviceDB()
        cls.MULTI_DEVICE_ZIP = MultiDeviceDB()
        cls.ARTIFACT_ZIP     = ArtifactDB()
        cls.UTF_ARTIFACT_ZIP = ArtifactDB(True)


    @classmethod
    def tearDownClass(cls):
        cls.EMPTY_ZIP.clear()
        cls.ONE_DEVICE_ZIP.clear()
        cls.MULTI_DEVICE_ZIP.clear()
        cls.ARTIFACT_ZIP.clear()
        cls.UTF_ARTIFACT_ZIP.clear()


    def _unzip(self, filename, directory):
        with zipfile.ZipFile(filename) as tmpzip:
            tmpzip.extractall(path = directory)


    def testInvalidDump(self):
        # file/directory does not exist
        for i in range(0, 10):
            name = "no_such_file_or_directory{}".format(i)
            if os.path.exists(name):
                continue

            with self.assertRaises(ccdb_dump.CC.Exception):
                ccdb_dump.CCDB_Dump.load(name)

        # file is not a zipfile
        with mkstemp() as (tmpfile, tmpfilepath):
            with self.assertRaises(zipfile.BadZipfile):
                ccdb_dump.CCDB_Dump.load(tmpfilepath)

        # directory is empty
        with mkdtemp(prefix = "testInvalidDump.emptydir-1") as tmpdirpath:
            with self.assertRaises(ccdb_dump.CC.Exception):
                ccdb_dump.CCDB_Dump.load(tmpdirpath)

        # directory is empty
        with mkdtemp(prefix = "testInvalidDump.emptydir-2") as tmpdirpath:
            os.mkdir(os.path.join(tmpdirpath, "ccdb"))
            with self.assertRaises(ccdb_dump.CC.Exception):
                ccdb_dump.CCDB_Dump.load(tmpdirpath)

        # empty device.dict
        with mkdtemp(prefix = "testInvalidDump.emptydevice.dict") as tmpdirpath:
            open(os.path.join(tmpdirpath, ccdb_dump.CC.DEVICE_DICT), "w").close()
            with self.assertRaises(ccdb_dump.CC.Exception):
                ccdb_dump.CCDB_Dump.load(tmpdirpath)

        # empty zip
        with mkstemp(suffix = ".ccdb.zip") as (tmpfile, tmpfilepath):
            with os.fdopen(tmpfile, 'wb') as tmpfilefile:
                with zipfile.ZipFile(tmpfilefile, mode = 'w'):
                    pass
            with self.assertRaises(ccdb_dump.CC.Exception):
                ccdb_dump.CCDB_Dump.load(tmpfilepath)


    def _testEmpty(self, cc_obj):
        self.assertFalse(cc_obj.getAllDeviceNames())
        self.assertFalse(cc_obj.getSimilarDeviceNames("")[1])
        with self.assertRaises(ccdb_dump.CC.Exception):
            cc_obj.device("no-such-device")
        self._testDownload(cc_obj)


    def _testOneDevice(self, cc_obj):
        alldevice = cc_obj.getAllDeviceNames()
        self.assertIsInstance(alldevice, list)
        self.assertEqual(alldevice, ["device"])
        (filtered, topxsimilar) = cc_obj.getSimilarDeviceNames("")
        self.assertFalse(filtered)
        self.assertIsInstance(topxsimilar, list)
        self.assertEqual(topxsimilar, ["device"])
        with self.assertRaises(ccdb_dump.CC.Exception):
            cc_obj.device("no-such-device")
        device = cc_obj.device("device")
        self.assertIsInstance(device, ccdb_dump.CC.Device)
        self.assertEqual(cc_obj.get_root_device(), device)
        self.assertEqual(device.name(), "device")
        self.assertEqual(str(device), "device")
        self.assertEqual(device["name"], "device")
        self.assertEqual(device.artifacts(), [])
        self.assertEqual(device.artifactNames(), [])
        self.assertEqual(device.externalLinks(), [])
        self.assertEqual(device.controls(), [])
        self.assertEqual(device.controlledBy(), [])
        self.assertEqual(device.controlledBy(True), [])
        self.assertEqual(device.properties(), {})
        self.assertEqual(device.propertiesDict(), {})
        self.assertIsInstance(device.description(), str)
        self.assertEqual(device.buildControlsList(), [])
        self.assertEqual(device.buildControlsList(include_self = True), [device])
        class HashObj(object):
            def __init__(self):
                super(HashObj, self).__init__()
                self.result = ""

            def update(self, string):
                if self.result:
                    self.result += ", " + string
                else:
                    self.result = string

        hashobj = HashObj()
        cc_obj.computeHash(hashobj)
        self.assertEqual(hashobj.result, "device, artifacts, , children, , controlledBy, , controls, , description, , deviceType, type, name, device, parents, , poweredBy, , powers, , properties, , slotType, SLOT")
#        print("BACKTRACK:", device.backtrack(""))
        self.assertIsNone(device.downloadArtifact("no-such-extension"))
        self.assertIsNone(device.downloadExternalLink("no-such-link", ""))
        self._testDownload(cc_obj)


    def _testMultiDevice(self, cc_obj):
        self.assertEqual(len(cc_obj.getAllDeviceNames()), 5)
        self.assertEqual(len(cc_obj.getSimilarDeviceNames("")[1]), 5)
        with self.assertRaises(ccdb_dump.CC.Exception):
            cc_obj.device("no-such-device")
        device = cc_obj.device("root")
        self.assertIsInstance(device, ccdb_dump.CC.Device)
        self.assertEqual(cc_obj.get_root_device(), device)
        self.assertEqual(len(device.controls()), MultiDeviceDB.num_of_directly_controlled_devices)

        level1 = cc_obj.device("foo1_level1")
        ctrld_by = level1.controlledBy()
        self.assertIsInstance(ctrld_by, list)
        self.assertEqual(len(ctrld_by), 1)
        self.assertEqual(ctrld_by[0].name(), "root")
        self.assertEqual(level1.controlledBy(True), [])

        ctrls_list = device.buildControlsList()
        self.assertIsInstance(ctrls_list, list)
        self.assertTrue(ctrls_list)
        self.assertEqual(list(map(lambda x: str(x), ctrls_list)), MultiDeviceDB.controls_list)

        self_ctrls_list = device.buildControlsList(include_self = True, verbose = True)
        self.assertIsInstance(self_ctrls_list, list)
        self.assertTrue(self_ctrls_list)
        self.assertEqual(self_ctrls_list[0], device)
        self.assertEqual(self_ctrls_list[1:], ctrls_list)

        ctrld_by = level1.controlledBy(True)
        self.assertIsInstance(ctrld_by, list)
        self.assertEqual(len(ctrld_by), 1)
        self.assertEqual(ctrld_by[0].name(), "root")

        self._testDownload(cc_obj)


    def _testArtifact(self, cc_obj, test_obj):
        self.assertEqual(cc_obj.getSimilarDeviceNames("")[1], ["device"])
        with self.assertRaises(ccdb_dump.CC.Exception):
            cc_obj.device("no-such-device")
        device = cc_obj.device("device")
        self.assertIsInstance(device, ccdb_dump.CC.Device)
        self.assertEqual(device.name(), "device")
        self.assertEqual(str(device), "device")
        self.assertEqual(device["name"], "device")
        artifacts = device.artifacts()
        self.assertTrue(artifacts)
        self.assertIsInstance(artifacts, list)
        # Right now artifacts include external links too
        self.assertEqual(len(artifacts), len(test_obj.artifacts) + len(test_obj.links))
        externalLinks = device.externalLinks()
        self.assertTrue(externalLinks)
        self.assertIsInstance(externalLinks, list)
        self.assertEqual(len(externalLinks), len(test_obj.links))
        artifact = artifacts[0]
        self.assertTrue(artifact)
        self.assertIsInstance(artifact, ccdb_dump.CC.Artifact)
        self.assertTrue(artifact.is_file())
        self.assertEqual(sorted(device.artifactNames()), sorted(test_obj.artifacts))

        # Check simple extension
        dArtifact = device.downloadArtifact(ArtifactDB.pyext)
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertEqual(os.path.basename(fname), ArtifactDB.artifact_py)
        self.assertTrue(filecmp.cmp(fname, test_obj.artifact_py, shallow = False), "Files are not identical: {} vs {}".format(fname, test_obj.artifact_py))

        # Check device precedence extension
        dArtifact = device.downloadArtifact(ArtifactDB.txtext)
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertEqual(os.path.basename(fname), ArtifactDB.device_artifact_txt)
        self.assertTrue(filecmp.cmp(fname, test_obj.device_artifact_txt, shallow = False), "Files are not identical: {} vs {}".format(fname, test_obj.device_artifact_txt))

        # Check extension with device tag
        dArtifact = device.downloadArtifact(ArtifactDB.txtext[1:], device_tag = ArtifactDB.tag)
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertEqual(os.path.basename(fname), ArtifactDB.test_artifact_txt)
        self.assertTrue(filecmp.cmp(fname, test_obj.test_artifact_txt, shallow = False), "Files are not identical: {} vs {}".format(fname, test_obj.test_artifact_txt))

        # Check non existent artifact
        self.assertIsNone(device.downloadArtifact("no-such-extension"))

        def no_filter(artifact, *args):
            return True

        # Check multiple artifact exception with an accept-everything filter
        with self.assertRaises(ccdb_dump.CC.ArtifactException):
            device.downloadArtifact("", custom_filter = no_filter)

        # Check non existent link
        self.assertIsNone(device.downloadExternalLink("no-such-link", ""))

        # Check inconsistent CCDB dump regarding not downloaded external links
        with self.assertRaises(ccdb_dump.CC.Exception):
            device.downloadExternalLink(ArtifactDB.epi, "no-such-extension")

        # Check multiple external links
        with self.assertRaises(ccdb_dump.CC.ArtifactException):
            device.downloadExternalLink("BEAST TREE", "", filetype = "Alarm tree")

        # Check external link
        dArtifact = device.downloadExternalLink(ArtifactDB.epi, "def", filetype = "Interface Definition")
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertTrue(filecmp.cmp(fname, test_obj.epi_file, shallow = 0), "Files are not identical: {} vs {}".format(fname, test_obj.epi_file))

        # Check external link with device tag
        dArtifact = device.downloadExternalLink(ArtifactDB.epi, "def", device_tag = ArtifactDB.tag, filetype = "Interface Definition")
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertTrue(filecmp.cmp(fname, test_obj.test_epi_file, shallow = 0), "Files are not identical: {} vs {}".format(fname, test_obj.test_epi_file))

        # Check external link with specified filename
        dArtifact = device.downloadExternalLink(ArtifactDB.beast, "alarms", filetype = "Alarm definition")
        self.assertTrue(dArtifact)
        fname = dArtifact.saved_as()
        self.assertTrue(fname)
        self.assertTrue(filecmp.cmp(fname, test_obj.speced_epi_file, shallow = 0), "Files are not identical: {} vs {}".format(fname, test_obj.speced_epi_file))


    def _testDownload(self, cc_obj):
        with self.assertRaises(ccdb_dump.CC.DownloadException):
            cc_obj.download_from_ccdb("empty-url", "no-such-artifact")

        with self.assertRaises(ccdb_dump.CC.DownloadException):
            cc_obj.download("empty-url", "no-such-artifact")


    def testEmptyZip(self):
        cc_obj = ccdb_dump.CCDB_Dump.load(str(self.EMPTY_ZIP))
        self._testEmpty(cc_obj)


    def testOneDeviceZip(self):
        cc_obj = ccdb_dump.CCDB_Dump.load(str(self.ONE_DEVICE_ZIP))
        self._testOneDevice(cc_obj)


    def testMultiDeviceZip(self):
        cc_obj = ccdb_dump.CCDB_Dump.load(str(self.MULTI_DEVICE_ZIP))
        self._testMultiDevice(cc_obj)


    def testArtifactZip(self):
        cc_obj = ccdb_dump.CCDB_Dump.load(str(self.ARTIFACT_ZIP))
        self._testArtifact(cc_obj, self.ARTIFACT_ZIP)


    def testUTFArtifactZip(self):
        cc_obj = ccdb_dump.CCDB_Dump.load(str(self.UTF_ARTIFACT_ZIP))
        self._testArtifact(cc_obj, self.UTF_ARTIFACT_ZIP)


    def testEmptyDir(self):
        with mkdtemp(prefix = "testEmptyDir") as tmpdirpath:
            self._unzip(str(self.EMPTY_ZIP), tmpdirpath)
            cc_obj = ccdb_dump.CCDB_Dump.load(tmpdirpath)
            self._testEmpty(cc_obj)


    def testOneDeviceDir(self):
        with mkdtemp(prefix = "testOneDeviceDir") as tmpdirpath:
            self._unzip(str(self.ONE_DEVICE_ZIP), tmpdirpath)
            cc_obj = ccdb_dump.CCDB_Dump.load(tmpdirpath)
            self._testOneDevice(cc_obj)


    def testMultiDeviceDir(self):
        with mkdtemp(prefix = "testMultiDeviceDir") as tmpdirpath:
            self._unzip(str(self.MULTI_DEVICE_ZIP), tmpdirpath)
            cc_obj = ccdb_dump.CCDB_Dump.load(tmpdirpath)
            self._testMultiDevice(cc_obj)


    def testArtifactDir(self):
        with mkdtemp(prefix = "testArtifactDir") as tmpdirpath:
            self._unzip(str(self.ARTIFACT_ZIP), tmpdirpath)
            cc_obj = ccdb_dump.CCDB_Dump.load(tmpdirpath)
            self._testArtifact(cc_obj, self.ARTIFACT_ZIP)


    def testUTFArtifactDir(self):
        with mkdtemp(prefix = "testUTFArtifactDir") as tmpdirpath:
            self._unzip(str(self.UTF_ARTIFACT_ZIP), tmpdirpath)
            cc_obj = ccdb_dump.CCDB_Dump.load(tmpdirpath)
            self._testArtifact(cc_obj, self.UTF_ARTIFACT_ZIP)



class TestCCDB(unittest.TestCase):
    def setUp(self):
        self.ccdb = ccdb.CCDB.open()


    def tearDown(self):
        self.ccdb = None


    def testNoSuchDevice(self):
        with self.assertRaises(ccdb.CCDB.NoSuchDeviceException):
            self.ccdb.device("no-such-device")


    def testSimilarDevices(self):
        devname = "VacS-ACCV:Vac-PLC-01001"
        with self.assertRaises(ccdb.CCDB.NoSuchDeviceException):
            self.ccdb.device(devname.lower())

        maxSim = 5
        (filtered, similarDevices) = self.ccdb.getSimilarDeviceNames(devname.lower(), maxSim)
        self.assertTrue(filtered)
        self.assertIsInstance(similarDevices, list)
        self.assertTrue(similarDevices)
        self.assertTrue(len(similarDevices) <= maxSim)
        self.assertTrue(len(similarDevices) > 1)
        self.assertEqual(similarDevices[0], devname)


    def testRootDevice(self):
        devname = "VacS-ACCV:Vac-PLC-01001"
        device = self.ccdb.device(devname)
        self.assertIsInstance(device, ccdb.CCDB.Device)
        self.assertEqual(device.name(), devname)

        controlsList = device.buildControlsList(include_self = True)
        self.assertIsInstance(controlsList, list)
        self.assertTrue(controlsList)
        self.assertEqual(device, controlsList[0])
        for dev in controlsList:
            self.assertIsInstance(dev, ccdb.CCDB.Device)

        # TODO: should run the same tests on the saved file as on the actual CCDB
        with mkstemp() as (tmpfile, tmpfilepath):
            with os.fdopen(tmpfile, 'wb') as fo:
                self.ccdb.save(fo)


    def testEPI(self):
        devname = "LEBT-010:Vac-VVS-20000"
        device = self.ccdb.device(devname)
        self.assertIsInstance(device, ccdb.CCDB.Device)
        self.assertEqual(device.name(), devname)

        # TODO: should download the actual .def file and filecmp
        self.assertIsInstance(device.downloadExternalLink("EPI", "def", filetype = "Interface Definition"), ccdb.CC.DownloadedArtifact)
        self.assertIsInstance(device.downloadExternalLink("EPI", "def", git_tag = "v4.0.1", filetype = "Interface Definition"), ccdb.CC.DownloadedArtifact)
        self.assertIsInstance(device.downloadExternalLink("EPI", "def", device_tag = "MPSVAC", filetype = "Interface Definition"), ccdb.CC.DownloadedArtifact)
        self.assertIsNone(device.downloadExternalLink("EPI", "def", device_tag = "no-such-tag", filetype = "Interface Definition"))




if __name__ == "__main__":
    unittest.main()
