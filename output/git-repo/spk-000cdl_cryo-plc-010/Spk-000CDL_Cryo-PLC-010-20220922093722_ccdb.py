#!/usr/bin/env python2

import os
import sys

sys.path.append(os.path.curdir)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ccdb_factory import CCDB_Factory

factory = CCDB_Factory()

# External links for ICS_CV_PB_SIPART
factory.addLink("ICS_CV_PB_SIPART", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_EH
factory.addLink("ICS_EH", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_HV
factory.addLink("ICS_HV", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# External links for ICS_LT
factory.addLink("ICS_LT", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# Artifacts for C3S_PID
factory.addArtifact("C3S_PID", "C3S_PID.def")

# External links for ICS_PT_mbar
factory.addLink("ICS_PT_mbar", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")
# Artifacts for ICS_PT_mbar
factory.addArtifact("ICS_PT_mbar", "VACUUM_VAC-VGx_TEMPLATE_ARCHIVE.txt")

# External links for ICS_LAKESHORE_TT
factory.addLink("ICS_LAKESHORE_TT", "EPI", "https://gitlab.esss.lu.se/icshwi/ics_library_definitions")

# Artifacts for C3S_AUTO_CONF
factory.addArtifact("C3S_AUTO_CONF", "C3S_AUTO_CONF.def")

# Artifacts for C3S_DIAG
factory.addArtifact("C3S_DIAG", "C3S_DIAG.def")

# Artifacts for C3S_INTLCK
factory.addArtifact("C3S_INTLCK", "C3S_INTLCK.def")

# Artifacts for C3S_MODE_SEL
factory.addArtifact("C3S_MODE_SEL", "C3S_MODE_SEL.def")

#
# Adding PLC: Spk-000CDL:Cryo-PLC-010
#
plc = factory.addPLC("Spk-000CDL:Cryo-PLC-010")
# Properties
plc.setProperty("PLCF#PLC-EPICS-COMMS: DiagPort", "2001")
plc.setProperty("PLCF#PLC-DIAG:Max-IO-Devices", "60")
plc.setProperty("PLCF#PLC-DIAG:Max-Modules-In-IO-Device", "30")
plc.setProperty("EPICSModule", [])
plc.setProperty("EPICSSnippet", [])
plc.setProperty("PLCF#PLC-EPICS-COMMS:Endianness", "BigEndian")
plc.setProperty("PLCF#EPICSToPLCDataBlockStartOffset", "0")
plc.setProperty("PLCF#PLCToEPICSDataBlockStartOffset", "0")
plc.setProperty("PLCF#PLC-EPICS-COMMS: MBConnectionID", "255")
plc.setProperty("PLCF#PLC-EPICS-COMMS: MBPort", "502")
plc.setProperty("PLCF#PLC-EPICS-COMMS: S7ConnectionID", "256")
plc.setProperty("PLCF#PLC-EPICS-COMMS: S7Port", "2000")
plc.setProperty("PLCF#PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
plc.setProperty("Hostname", "cds-plc-spk-000.tn.esss.lu.se")
plc.setProperty("PLCF#PLC-DIAG:Max-Local-Modules", "30")
plc.setProperty("PLCF#PLC-EPICS-COMMS: DiagConnectionID", "254")
plc.setProperty("PLC-EPICS-COMMS: GatewayDatablock", null)
plc.setProperty("PLCF#PLC-EPICS-COMMS: InterfaceID", "72")

#
# Adding device Spk-000CDL:Cryo-CV-91 of type ICS_CV_PB_SIPART
#
dev = plc.addDevice("ICS_CV_PB_SIPART", "Spk-000CDL:Cryo-CV-91")

#
# Adding device Spk-000CDL:Cryo-CV-92 of type ICS_CV_PB_SIPART
#
dev = plc.addDevice("ICS_CV_PB_SIPART", "Spk-000CDL:Cryo-CV-92")

#
# Adding device Spk-000CDL:Cryo-CV-93 of type ICS_CV_PB_SIPART
#
dev = plc.addDevice("ICS_CV_PB_SIPART", "Spk-000CDL:Cryo-CV-93")

#
# Adding device Spk-000CDL:Cryo-CV-94 of type ICS_CV_PB_SIPART
#
dev = plc.addDevice("ICS_CV_PB_SIPART", "Spk-000CDL:Cryo-CV-94")

#
# Adding device Spk-000CDL:Cryo-EH-91 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-91")

#
# Adding device Spk-000CDL:Cryo-EH-92 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-92")

#
# Adding device Spk-000CDL:Cryo-EH-93 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-93")

#
# Adding device Spk-000CDL:Cryo-EH-94 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-94")

#
# Adding device Spk-000CDL:Cryo-EH-95 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-95")

#
# Adding device Spk-000CDL:Cryo-EH-96 of type ICS_EH
#
dev = plc.addDevice("ICS_EH", "Spk-000CDL:Cryo-EH-96")

#
# Adding device Spk-000CDL:Cryo-HV-70 of type ICS_HV
#
dev = plc.addDevice("ICS_HV", "Spk-000CDL:Cryo-HV-70")

#
# Adding device Spk-000CDL:Cryo-HV-73 of type ICS_HV
#
dev = plc.addDevice("ICS_HV", "Spk-000CDL:Cryo-HV-73")

#
# Adding device Spk-000CDL:Cryo-LT-91 of type ICS_LT
#
dev = plc.addDevice("ICS_LT", "Spk-000CDL:Cryo-LT-91")
# Properties
dev.setProperty("EGU", null)
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("ControllerDevice", "")

#
# Adding device Spk-000CDL:Cryo-LT-92 of type ICS_LT
#
dev = plc.addDevice("ICS_LT", "Spk-000CDL:Cryo-LT-92")
# Properties
dev.setProperty("EGU", null)
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("ControllerDevice", "")

#
# Adding device Spk-000CDL:Vac-VGP-070 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Vac-VGP-070")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Vac-VGC-071 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Vac-VGC-071")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-PT-91 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Cryo-PT-91")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-PT-92 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Cryo-PT-92")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-PT-93 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Cryo-PT-93")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-PT-94 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Cryo-PT-94")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-PT-95 of type ICS_PT_mbar
#
dev = plc.addDevice("ICS_PT_mbar", "Spk-000CDL:Cryo-PT-95")
# Properties
dev.setProperty("EPICSModule", [])
dev.setProperty("EPICSSnippet", [])
dev.setProperty("MKSChannel", null)
dev.setProperty("TPGChannel", null)

#
# Adding device Spk-000CDL:Cryo-TT-91 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-91")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-92 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-92")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-93 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-93")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-94 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-94")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-95 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-95")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-96 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-96")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-97 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-97")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:Cryo-TT-98 of type ICS_LAKESHORE_TT
#
dev = plc.addDevice("ICS_LAKESHORE_TT", "Spk-000CDL:Cryo-TT-98")
# Properties
dev.setProperty("EGU", "K")

#
# Adding device Spk-000CDL:SC-FSM-400 of type C3S_DIAG
#
dev = plc.addDevice("C3S_DIAG", "Spk-000CDL:SC-FSM-400")

#
# Adding device Spk-000CDL:SC-FSM-500 of type C3S_INTLCK
#
dev = plc.addDevice("C3S_INTLCK", "Spk-000CDL:SC-FSM-500")

#
# Adding device Spk-000CDL:SC-FSM-600 of type C3S_MODE_SEL
#
dev = plc.addDevice("C3S_MODE_SEL", "Spk-000CDL:SC-FSM-600")

#
# Adding device Spk-000CDL:Cryo-PID-91 of type C3S_PID
#
dev = plc.addDevice("C3S_PID", "Spk-000CDL:Cryo-PID-91")

#
# Adding device Spk-000CDL:Cryo-PID-92 of type C3S_PID
#
dev = plc.addDevice("C3S_PID", "Spk-000CDL:Cryo-PID-92")

#
# Adding device Spk-000CDL:Cryo-PID-93 of type C3S_PID
#
dev = plc.addDevice("C3S_PID", "Spk-000CDL:Cryo-PID-93")

#
# Adding device Spk-000CDL:Cryo-PID-94 of type C3S_PID
#
dev = plc.addDevice("C3S_PID", "Spk-000CDL:Cryo-PID-94")

#
# Adding device Spk-000CDL:SC-FSM-300 of type C3S_AUTO_CONF
#
dev = plc.addDevice("C3S_AUTO_CONF", "Spk-000CDL:SC-FSM-300")


#
# Saving the created CCDB
#
factory.save("Spk-000CDL:Cryo-PLC-010")
