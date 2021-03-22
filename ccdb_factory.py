#!/usr/bin/env python2

from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: CCDB constructor """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


import sys
if sys.version_info.major != 2:
    print("""
Python-3 support is experimental
""", file = sys.stderr)
#    raise RuntimeError("CCDBFactory supports Python-2.x only. You are running " + sys.version)

# Python libraries
import os
from shutil import copy2

# PLCFactory modules
from cc import CC
from ccdb import CCDB



class CCDB_Factory(CC):
    data_types = dict({ str: "String", int: "Integer", list : "Strings List" })

    default_artifact_dict = {"kind": "TYPE",
                             "description": "",
                             "type": "FILE",
                             "uri" : None,
                             "name": None}

    default_link_dict     = {"kind": "TYPE",
                             "description": "",
                             "type": "URI",
                             "uri" : None,
                             "name": None}

    default_prop_dict     = {"dataType": "String",
                             "value": None,
                             "kind": "TYPE",
                             "name": None,
                             "unit": None}


    @staticmethod
    def toDatatype(value, dataType = None):
        if dataType is not None:
            if dataType in CCDB_Factory.data_types.values():
                return dataType

            try:
                return CCDB_Factory.data_types[dataType]
            except KeyError:
                raise CC.Exception("Unknown data type: {}".format(dataType))

        if isinstance(value, str):
            dataType = "String"
        elif isinstance(value, int):
            dataType = "Integer"
        elif isinstance(value, list):
            try:
                if isinstance(value[0], str):
                    dataType = "Strings List"
            except IndexError:
                raise CC.Exception("Unable to auto-detect dataType for {}".format(value))

        if dataType is None:
            raise CC.Exception("Unable to auto-detect dataType for {}".format(value))

        return dataType


    @staticmethod
    def checkIfExists(filename):
        if not os.access(filename, os.R_OK):
            raise CC.Exception("Cannot find file '{}'".format(filename))



    @staticmethod
    def checkArtifact(artifacts, artifact):
        """
        Check if artifact is unique. Returns True if artifact should be added, False otherwise
        """
        if not isinstance(artifacts, list):
            return True

        for art in artifacts:
            if art["kind"] == artifact["kind"] and art["name"] == artifact["name"]:
                if art != artifact:
                    raise CC.Exception("Duplicate entries: {} and {}".format(art, artifact))
                else:
                    return False

        return True



    class Artifact(CCDB.Artifact):
        prepare_to_download = CC.Artifact.prepare_to_download

        def save(self, git_tag = None):
            if self.is_file():
                self._saveasurl = self._artifact["full_path"]
                self.download()
            elif self._artifact["download"]:
                name = self.name()
                if name.startswith("EPI"):
                    extension = ".def"
                elif name.startswith("BEAST TREE"):
                    extension = ".alarm-tree"
                elif name.startswith("BEAST TEMPLATE"):
                    extension = ".alarms-template"
                elif name.startswith("BEAST"):
                    extension = ".alarms"
                else:
                    raise CC.Exception("Unable to auto-detect extension for {}".format(name))

                # git-tag
                self.downloadExternalLink(self._device.defaultFilename(extension), extension, git_tag)


        def _download(self, save_as):
            if self.is_file():
                copy2(self._artifact["full_path"], save_as)
            else:
                try:
                    full_path = self._artifact["full_path"]
                    if os.path.isdir(full_path):
                        full_path = os.path.join(full_path, os.path.basename(save_as))
                    copy2(full_path, save_as)
                except KeyError:
                    super(CCDB_Factory.Artifact, self)._download(save_as)



    class Device(CCDB.Device):
        # Leave everything (that is not a string) as None here
        # Change the value after an instance has been created
        default_device_dict = {"slotType"     : "SLOT",
                               "name"         : None,
                               "deviceType"   : None,
                               "description"  : None,
                               "artifacts"    : None,
                               "controls"     : None,
                               "controlledBy" : None,
                               "properties"   : None,
                               "children"     : None,
                               "parents"      : None,
                               "powers"       : None,
                               "poweredBy"    : None}


        def __init__(self, deviceName, deviceType = None, ccdb = None):
            super(CCDB_Factory.Device, self).__init__(dict(CCDB_Factory.Device.default_device_dict), ccdb = ccdb)
            self._slot["name"] = deviceName
            if deviceType is not None:
                self._slot["deviceType"] = deviceType


        def _artifact(self, a):
            return CCDB_Factory.Artifact(self, a)


        def save(self, git_tag = None):
            for artifact in self.artifacts():
                artifact.save(git_tag)


        def setControls(self, value):
            if not isinstance(value, list):
                value = [ value ]

            devnames = []
            for devname in value:
                if isinstance(devname, CCDB_Factory.Device):
                    devname = devname.name()
                devnames.append(devname)

            try:
                self._slot["controls"].extend(devnames)
            except AttributeError:
                # Handle 'controls' is None case
                self._slot["controls"] = devnames

            for deviceName in devnames:
                device = self.ccdb.device(deviceName)
                try:
                    already = set(device._slot["controlledBy"])
                    already.add(self.name())
                    device._slot["controlledBy"] = list(already)
                except TypeError:
                    # Handle 'controlledBy' is None case
                    device._slot["controlledBy"] = [ self.name() ]


        def setProperty(self, key, value, dataType = None):
            if self._slot["properties"] is None:
                self._slot["properties"] = []

            str_value = str(value) if value is not None else None
            for prop in self._slot["properties"]:
                if prop["name"] == key:
                    prop["value"] = str_value
                    return

            self._slot["properties"].append({"name": key, "value": str_value, "dataType": CCDB_Factory.toDatatype(value, dataType)})


        def addDevice(self, deviceType, deviceName):
            device = self.ccdb.addDevice(deviceType, deviceName)
            self.setControls(deviceName)

            return device


        def addPLC(self, deviceName):
            device = self.ccdb.addPLC(deviceName)
            self.setControls(deviceName)

            return device


        def addBECKHOFF(self, deviceName):
            device = self.ccdb.addBECKHOFF(deviceName)
            self.setControls(deviceName)

            return device


        def __addArtifact(self, artifactDict):
            if not CCDB_Factory.checkArtifact(self._slot["artifacts"], artifactDict):
                return
            try:
                self._slot["artifacts"].append(artifactDict)
            except AttributeError:
                # Handle 'artifacts' is None case
                self._slot["artifacts"] = [ artifactDict ]


        def addArtifact(self, name, local_file = None):
            if local_file is None:
                local_file = name

            if os.path.isdir(local_file):
                local_file = os.path.join(local_file, name)
            CCDB_Factory.checkIfExists(local_file)

            artifactDict = dict(CCDB_Factory.default_artifact_dict)
            artifactDict["kind"]      = "SLOT"
            artifactDict["name"]      = os.path.basename(name)
            artifactDict["full_path"] = local_file

            self.__addArtifact(artifactDict)


        def addLink(self, name, uri, local_file = None, download = True):
            artifactDict = dict(CCDB_Factory.default_link_dict)
            artifactDict["kind"] = "SLOT"
            artifactDict["name"] = name
            artifactDict["uri"]  = uri
            artifactDict["download"] = download
            if local_file is not None:
                if not os.path.isdir(local_file):
                    CCDB_Factory.checkIfExists(local_file)
                artifactDict["full_path"] = local_file

            self.__addArtifact(artifactDict)



    def __init__(self, git_tag = None):
        super(CCDB_Factory, self).__init__()
        CCDB_Factory.Device.ccdb = self
        self._git_tag    = git_tag
        self._artifacts  = dict()
        self._properties = dict()
        self._saved_as   = None


    def addPLC(self, deviceName):
        plc = self.addDevice("PLC", deviceName)
        plc._slot["properties"] = [{'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSModule', 'unit': None},
                                   {'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSSnippet', 'unit': None},
                                   {'dataType': 'String', 'value': 'EPICSToPLC', 'kind': 'SLOT', 'name': 'PLCF#EPICSToPLCDataBlockName', 'unit': None},
                                   {'dataType': 'String', 'value': 'PLCToEPICS', 'kind': 'SLOT', 'name': 'PLCF#PLCToEPICSDataBlockName', 'unit': None},
                                   {'dataType': 'Integer', 'value': '0', 'kind': 'SLOT', 'name': 'PLCF#EPICSToPLCDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '0', 'kind': 'SLOT', 'name': 'PLCF#PLCToEPICSDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '502', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBPort', 'unit': None},
                                   {'dataType': 'Integer', 'value': '255', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '256', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: S7ConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '2000', 'kind': 'SLOT','name': 'PLCF#PLC-EPICS-COMMS: S7Port', 'unit': None},
                                   {'dataType': 'Endianness', 'value': 'BigEndian', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS:Endianness', 'unit': None},
                                   {'dataType': 'String', 'value': '64', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: InterfaceID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '1', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-IO-Devices', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Local-Modules', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Modules-In-IO-Device', 'unit': None},
                                   {'dataType': 'String', 'value': 'Pulse_200ms', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: PLCPulse', 'unit': None},
                                  ]
        return plc


    def addBECKHOFF(self, deviceName):
        plc = self.addDevice("PLC_BECKHOFF", deviceName)
        plc._slot["properties"] = [{'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSModule', 'unit': None},
                                   {'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSSnippet', 'unit': None},
                                   {'dataType': 'Integer', 'value': '12288', 'kind': 'SLOT', 'name': 'PLCF#EPICSToPLCDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '0', 'kind': 'SLOT', 'name': 'PLCF#PLCToEPICSDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '502', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBPort', 'unit': None},
                                   {'dataType': 'Integer', 'value': '255', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '256', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: S7ConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '2000', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: S7Port', 'unit': None},
                                   {'dataType': 'Endianness', 'value': 'LittleEndian', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS:Endianness', 'unit': None},
                                   {'dataType': 'String', 'value': '16#40', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: InterfaceID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '1', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-IO-Devices', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Local-Modules', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Modules-In-IO-Device', 'unit': None}]
        return plc


    def addDevice(self, deviceType, deviceName):
        device = self.device(deviceName)

        if device._slot["deviceType"] is None:
            device._slot["deviceType"] = deviceType
            try:
                artifact = self._artifacts[deviceType]
                try:
                    device._slot["artifacts"].append(artifact)
                except AttributeError:
                    # Handle 'artifacts' is None case
                    device._slot["artifacts"] = list(artifact)
            except KeyError:
                # No artifact for this deviceType
                pass

            try:
                properties = self._properties[deviceType]
                try:
                    device._slot["properties"].append(properties)
                except AttributeError:
                    # Handle 'properties' is None case
                    device._slot["properties"] = list(properties)
            except KeyError:
                # No properties for this deviceType
                pass


        return device


    def _device(self, deviceName):
        device = CCDB_Factory.Device(deviceName)
        self._devices[deviceName] = device
        return device


    def __addArtifact(self, deviceType, artifactDict):
        if not CCDB_Factory.checkArtifact(self._artifacts.get(deviceType), artifactDict):
            return
        try:
            self._artifacts[deviceType].append(artifactDict)
        except KeyError:
            self._artifacts[deviceType] = [ artifactDict ]


    def addArtifact(self, deviceType, name, local_file = None):
        if local_file is None:
            local_file = name

        if os.path.isdir(local_file):
            local_file = os.path.join(local_file, name)
        CCDB_Factory.checkIfExists(local_file)

        artifactDict = dict(CCDB_Factory.default_artifact_dict)
        artifactDict["name"]      = os.path.basename(name)
        artifactDict["full_path"] = local_file

        self.__addArtifact(deviceType, artifactDict)


    def addLink(self, deviceType, name, uri, local_file = None, download = True):
        artifactDict = dict(CCDB_Factory.default_link_dict)
        artifactDict["uri"]  = uri
        artifactDict["name"] = name
        artifactDict["download"] = download
        if local_file is not None:
            if not os.path.isdir(local_file):
                CCDB_Factory.checkIfExists(local_file)
            artifactDict["full_path"] = local_file

        self.__addArtifact(deviceType, artifactDict)


    def setProperty(self, deviceType, key, value, dataType = None):
        propDict = dict(CCDB_Factory.default_prop_dict)
        propDict["name"]  = key
        propDict["value"] = str(value) if value is not None else None

        propDict["dataType"] = self.toDatatype(value, dataType)

        try:
            self._properties[deviceType].append(propDict)
        except KeyError:
            self._properties[deviceType] = [ propDict ]


    def url(self):
        return "CCDB Factory at " + str(self._saved_as)


    def dump(self, filename, *pargs, **kwargs):
        return self.save(filename, *pargs, **kwargs)


    def save(self, filename, *pargs, **kwargs):
        self._saved_as = filename
        for device in self._devices.values():
            device.save(self._git_tag)

        return super(CCDB_Factory, self).save(filename, *pargs, **kwargs)





if __name__ == "__main__":
    # Create a CCDB factory
    factory = CCDB_Factory()

    # Add deviceType artifacts
    factory.addArtifact("VACUUM_VAC-VVS", "filename")

    # Add deviceType external links
    factory.addLink("VACUUM_VAC-VVS", "EPI",                    "https://bitbucket.org/europeanspallationsource/repository", "local_filename")
    factory.addLink("VACUUM_VAC-VVS", "EPI__tag[tag_filename]", "https://bitbucket.org/europeanspallationsource/repository")

    # Add the PLC
    plc = factory.addPLC("MPS-Vac:Ctrl-PLC-001")

    # Change some properties
    plc.setProperty('PLCF#PLC-EPICS-COMMS: InterfaceID', 666)

    # Add slot artifacts
    plc.addArtifact("plc_filename")

    valves = ["LEBT-010:Vac-VVS-20000", "LEBT-010:Vac-VVS-40000"]

    # Add other devices (implicitly sets controls/controlled-by relationship)
    for valve in valves:
        plc.addDevice("VACUUM_VAC-VVS", valve)

    # Add slot link to device
    factory.device("LEBT-010:Vac-VVS-20000").addLink("EPI__tag", "https://bitbucket.org/europeanspallationsource/repository2", "local_filename2")
    factory.device("LEBT-010:Vac-VVS-20000").addArtifact("slot_filename")

    # Dump our CCDB
    factory.save("my_ccdb")
