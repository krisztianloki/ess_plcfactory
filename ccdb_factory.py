from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: CCDB constructor """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
from os     import path as os_path
from shutil import copy2

# PLCFactory modules
from cc   import CC
from ccdb import CCDB



class CCDB_Factory(CC):
    default_artifact_dict = {"kind": "TYPE",
                             "description": "",
                             "type": "FILE",
                             "uri":  None,
                             "name": None}

    default_link_dict     = {"kind": "TYPE",
                             "description": "",
                             "type": "URI",
                             "uri":  None,
                             "name": None}

    default_prop_dict     = {"dataType": "String",
                             "value": None,
                             "kind": "TYPE",
                             "name": None,
                             "unit": None}


    @staticmethod
    def toDatatype(value, dataType = None):
        if dataType is not None:
            return dataType

        if isinstance(value, str):
            dataType = "String"
        elif isinstance(value, int):
            dataType = "Integer"
        elif isinstance(value, list):
            if isinstance(value[0], str):
                dataType = "Strings List"

        if dataType is None:
            raise RuntimeError("Unable to auto-detect dataType for {}".format(value))

        return dataType



    class Artifact(CCDB.Artifact):
        def dump(self):
            if self.is_file():
                self.download()
            else:
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
                    raise RuntimeError("Unable to auto-detect extension for {}".format(name))

                self.downloadExternalLink(self._device.defaultFilename(extension), extension)


        def _download(self, save_as, url = None):
            if self.is_file():
                copy2(self._artifact["full_path"], save_as)
            else:
                try:
                    copy2(self._artifact["full_path"], save_as)
                except KeyError:
                    super(CCDB_Factory.Artifact, self)._download(save_as, url)



    class Device(CCDB.Device):
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


        def __init__(self, deviceName, deviceType = None):
            super(CCDB_Factory.Device, self).__init__(dict(CCDB_Factory.Device.default_device_dict))
            self._slot["name"] = deviceName
            if deviceType is not None:
                self._slot["deviceType"] = deviceName


        def _artifact(self, a):
            return CCDB_Factory.Artifact(self, a)


        def dump(self):
            for artifact in self.artifacts():
                artifact.dump()


        def setControls(self, value):
            if not isinstance(value, list):
                value = [ value ]

            self._slot["controls"] = value

            for deviceName in value:
                device = CCDB_Factory.Device.ccdb.device(deviceName)
                try:
                    already = set(device._slot["controlledBy"])
                    already.add(self.name())
                    device._slot["controlledBy"] = list(already)
                except TypeError:
                    # Handle 'controlledBy' is None case
                    device._slot["controlledBy"] = [ self.name() ]


        def setProperty(self, key, value, dataType = None):
            for prop in self._slot["properties"]:
                if prop["name"] == key:
                    prop["value"] = str(value)
                    return

            self._slot["properties"].append({"name": key, "value": str(value), "dataType": CCDB_Factory.toDatatype(value, dataType)})


        def addArtifact(self, name, local_file = None):
            if local_file is None:
                local_file = name

            artifactDict = dict(CCDB_Factory.default_artifact_dict)
            artifactDict["kind"]      = "SLOT"
            artifactDict["name"]      = os_path.basename(name)
            artifactDict["full_path"] = local_file

            try:
                self._slot["artifacts"].append(artifactDict)
            except AttributeError:
                # Handle 'artifacts' is None case
                self._slot["artifacts"] = [ artifactDict ]


        def addLink(self, name, uri, local_file = None):
            artifactDict = dict(CCDB_Factory.default_link_dict)
            artifactDict["kind"] = "SLOT"
            artifactDict["name"] = name
            artifactDict["uri"]  = uri
            if local_file is not None:
                artifactDict["full_path"] = local_file

            try:
                self._slot["artifacts"].append(artifactDict)
            except AttributeError:
                # Handle 'artifacts' is None case
                self._slot["artifacts"] = [ artifactDict ]



    def __init__(self, user = None):
        super(CCDB_Factory, self).__init__(user)
        CCDB_Factory.Device.ccdb = self
        self._artifacts  = dict()
        self._properties = dict()


    def addPLC(self, deviceName):
        plc = self.addDevice("PLC", deviceName)
        plc._slot["properties"] = [{'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSModule', 'unit': None},
                                   {'dataType': 'Strings List', 'value': 'null', 'kind': 'SLOT', 'name': 'EPICSSnippet', 'unit': None},
                                   {'dataType': 'String', 'value': 'EPICSToPLC', 'kind': 'SLOT', 'name': 'PLCF#EPICSToPLCDataBlockName', 'unit': None},
                                   {'dataType': 'String', 'value': 'PLCToEPICS', 'kind': 'SLOT', 'name': 'PLCF#PLCToEPICSDataBlockName', 'unit': None},
                                   {'dataType': 'Integer', 'value': '0', 'kind': 'SLOT', 'name': 'PLCF#EPICSToPLCDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '0', 'kind': 'SLOT', 'name': 'PLCF#PLCToEPICSDataBlockStartOffset', 'unit': None},
                                   {'dataType': 'Integer', 'value': '2000', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: BytesToSend', 'unit': None},
                                   {'dataType': 'Integer', 'value': '502', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBPort', 'unit': None},
                                   {'dataType': 'Integer', 'value': '255', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: MBConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '256', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: S7ConnectionID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '2000', 'kind': 'SLOT','name': 'PLCF#PLC-EPICS-COMMS: S7Port', 'unit': None},
                                   {'dataType': 'Endianness', 'value': 'BigEndian', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS:Endianness', 'unit': None},
                                   {'dataType': 'String', 'value': '16#40', 'kind': 'SLOT', 'name': 'PLCF#PLC-EPICS-COMMS: InterfaceID', 'unit': None},
                                   {'dataType': 'Integer', 'value': '1', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-IO-Devices', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Local-Modules', 'unit': None},
                                   {'dataType': 'Integer', 'value': '10', 'kind': 'SLOT', 'name': 'PLCF#PLC-DIAG:Max-Modules-In-IO-Device', 'unit': None}]
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


    def addArtifact(self, deviceType, name, local_file = None):
        if local_file is None:
            local_file = name
        artifactDict = dict(CCDB_Factory.default_artifact_dict)
        artifactDict["name"]      = os_path.basename(name)
        artifactDict["full_path"] = local_file

        try:
            self._artifacts[deviceType].append(artifactDict)
        except KeyError:
            self._artifacts[deviceType] = [ artifactDict ]


    def addLink(self, deviceType, name, uri, local_file = None):
        artifactDict = dict(CCDB_Factory.default_link_dict)
        artifactDict["uri"]  = uri
        artifactDict["name"] = name
        if local_file is not None:
            artifactDict["full_path"] = local_file

        try:
            self._artifacts[deviceType].append(artifactDict)
        except KeyError:
            self._artifacts[deviceType] = [ artifactDict ]


    def setProperty(self, deviceType, key, value, dataType = None):
        propDict = dict(CCDB_Factory.default_prop_dict)
        propDict["name"]  = key
        propDict["value"] = value

        propDict["dataType"] = self.toDatatype(value, dataType)

        try:
            self._properties[deviceType].append(propDict)
        except KeyError:
            self._properties[deviceType] = [ propDict ]


    def dump(self, filename, *pargs, **kwargs):
        for device in self._devices.itervalues():
            device.dump()

        return super(CCDB_Factory, self).dump(filename, *pargs, **kwargs)





if __name__ == "__main__":
    # Create a CCDB factory
    factory = CCDB_Factory()

    # Add deviceType artifacts
    factory.addArtifact("VACUUM_VAC-VVS", "filename")

    # Add deviceType external links
    factory.addLink("VACUUM_VAC-VVS", "EPI",                    "https://bitbucket.org/europeanspallationsource/repository", "local_filename")
    factory.addLink("VACUUM_VAC-VVS", "EPI__tag[tag_filename]", "https://bitbucket.org/europeanspallationsource/repository")

    valves = ["LEBT-010:Vac-VVS-20000", "LEBT-010:Vac-VVS-40000"]

    # Add the PLC
    plc = factory.addPLC("MPS-Vac:Ctrl-PLC-001")

    # Set the controls relationship
    plc.setControls(valves)

    # Change some properties
    plc.setProperty('PLCF#PLC-EPICS-COMMS: InterfaceID', 666)

    # Add slot artifacts
    plc.addArtifact("plc_filename")

    # Add other devices
    for valve in valves:
        factory.addDevice("VACUUM_VAC-VVS", valve)

    # Add slot link to device
    factory.device("LEBT-010:Vac-VVS-20000").addLink("EPI__tag", "https://bitbucket.org/europeanspallationsource/repository2", "local_filename2")
    factory.device("LEBT-010:Vac-VVS-20000").addArtifact("slot_filename")

    # Dump our CCDB
    factory.dump("factory")
