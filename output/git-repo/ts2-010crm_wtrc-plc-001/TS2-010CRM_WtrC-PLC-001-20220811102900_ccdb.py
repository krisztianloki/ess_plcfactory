#!/usr/bin/env python2

import os
import sys

sys.path.append(os.path.curdir)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ccdb_factory import CCDB_Factory

factory = CCDB_Factory()

# External links for ICS_FIS
factory.addLink("ICS_FIS", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_PT
factory.addLink("ICS_PT", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_TT
factory.addLink("ICS_TT", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_PV
factory.addLink("ICS_PV", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

#
# Adding PLC: TS2-010CRM:WtrC-PLC-001
#
plc = factory.addPLC("TS2-010CRM:WtrC-PLC-001")
# Properties
plc.setProperty("PLCF#PLC-EPICS-COMMS: DiagConnectionID", "254")
plc.setProperty("PLCF#PLC-EPICS-COMMS: DiagPort", "2001")
plc.setProperty("EPICSModule", [])
plc.setProperty("EPICSSnippet", [])
plc.setProperty("PLCF#PLC-EPICS-COMMS:Endianness", "BigEndian")
plc.setProperty("PLCF#PLC-DIAG:Max-Modules-In-IO-Device", "60")
plc.setProperty("PLCF#PLC-DIAG:Max-IO-Devices", "20")
plc.setProperty("PLCF#EPICSToPLCDataBlockStartOffset", "0")
plc.setProperty("PLCF#PLCToEPICSDataBlockStartOffset", "0")
plc.setProperty("PLCF#PLC-EPICS-COMMS: MBConnectionID", "255")
plc.setProperty("PLCF#PLC-EPICS-COMMS: MBPort", "502")
plc.setProperty("Hostname", "ics-ts2wtrc-plc-01.tn.esss.lu.se")
plc.setProperty("PLCF#PLC-EPICS-COMMS: S7ConnectionID", "256")
plc.setProperty("PLCF#PLC-EPICS-COMMS: S7Port", "2000")
plc.setProperty("PLCF#PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
plc.setProperty("PLCF#PLC-DIAG:Max-Local-Modules", "60")
plc.setProperty("PLC-EPICS-COMMS: GatewayDatablock", null)
plc.setProperty("PLCF#PLC-EPICS-COMMS: InterfaceID", "72")

#
# Adding device TS2-010CRM:WtrC-FIS-101 of type ICS_FIS
#
dev = plc.addDevice("ICS_FIS", "TS2-010CRM:WtrC-FIS-101")

#
# Adding device TS2-010CRM:WtrC-FIS-102 of type ICS_FIS
#
dev = plc.addDevice("ICS_FIS", "TS2-010CRM:WtrC-FIS-102")

#
# Adding device TS2-010CRM:WtrC-PT-101 of type ICS_PT
#
dev = plc.addDevice("ICS_PT", "TS2-010CRM:WtrC-PT-101")
# Properties
dev.setProperty("EGU", "bar")

#
# Adding device TS2-010CRM:WtrC-PT-102 of type ICS_PT
#
dev = plc.addDevice("ICS_PT", "TS2-010CRM:WtrC-PT-102")
# Properties
dev.setProperty("EGU", "bar")

#
# Adding device TS2-010CRM:WtrC-FIS-104 of type ICS_FIS
#
dev = plc.addDevice("ICS_FIS", "TS2-010CRM:WtrC-FIS-104")

#
# Adding device TS2-010CRM:WtrC-YCV-101 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YCV-101")

#
# Adding device TS2-010CRM:WtrC-YCV-102 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YCV-102")

#
# Adding device TS2-010CRM:WtrC-YCV-103 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YCV-103")

#
# Adding device TS2-010CRM:WtrC-YCV-104 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YCV-104")

#
# Adding device TS2-010CRM:WtrC-YSV-109 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YSV-109")

#
# Adding device TS2-010CRM:WtrC-YSV-110 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YSV-110")

#
# Adding device TS2-010CRM:WtrC-YSV-111 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YSV-111")

#
# Adding device TS2-010CRM:WtrC-YSV-112 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YSV-112")

#
# Adding device TS2-010CRM:WtrC-YSV-113 of type ICS_PV
#
dev = plc.addDevice("ICS_PV", "TS2-010CRM:WtrC-YSV-113")

#
# Adding device TS2-010CRM:WtrC-FIS-103 of type ICS_FIS
#
dev = plc.addDevice("ICS_FIS", "TS2-010CRM:WtrC-FIS-103")

#
# Adding device TS2-010CRM:WtrC-TE-104 of type ICS_TT
#
dev = plc.addDevice("ICS_TT", "TS2-010CRM:WtrC-TE-104")
# Properties
dev.setProperty("EGU", "C")

#
# Adding device TS2-010CRM:WtrC-TE-103 of type ICS_TT
#
dev = plc.addDevice("ICS_TT", "TS2-010CRM:WtrC-TE-103")
# Properties
dev.setProperty("EGU", "C")

#
# Adding device TS2-010CRM:WtrC-TE-102 of type ICS_TT
#
dev = plc.addDevice("ICS_TT", "TS2-010CRM:WtrC-TE-102")
# Properties
dev.setProperty("EGU", "C")

#
# Adding device TS2-010CRM:WtrC-TE-101 of type ICS_TT
#
dev = plc.addDevice("ICS_TT", "TS2-010CRM:WtrC-TE-101")
# Properties
dev.setProperty("EGU", "C")


#
# Saving the created CCDB
#
factory.save("TS2-010CRM:WtrC-PLC-001")
