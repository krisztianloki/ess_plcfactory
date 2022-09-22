#!/bin/bash

# Script to start Spk-000CDL:SC-IOC-010

# This variable sets the base autosave directory; the actual autosave files will be in $(AS_TOP)/Spk-000CDL_SC-IOC-010/save
(
export AS_TOP=/tmp
export IOCNAME="Spk-000CDL:SC-IOC-010"
export IOCDIR="Spk-000CDL_SC-IOC-010"

source /epics/base-7.0.5/require/3.4.1/bin/setE3Env.bash

iocsh.bash /home/centos/plc-factory/plcfactory/output/spk-000cdl_cryo-plc-010/ioc/spk-000cdl_sc-ioc-010/st.cmd
)

