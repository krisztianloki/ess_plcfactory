#!/bin/bash

# Script to start TS2-010CRM:SC-IOC-920

# This variable sets the base autosave directory; the actual autosave files will be in $(AS_TOP)/TS2-010CRM_SC-IOC-920/save
(
export AS_TOP=/tmp
export IOCNAME="TS2-010CRM:SC-IOC-920"
export IOCDIR="TS2-010CRM_SC-IOC-920"

source /epics/base-7.0.5/require/3.4.1/bin/setE3Env.bash

iocsh.bash /home/centos/plc-factory/plcfactory/output/ts2-010crm_wtrc-plc-001/ioc/ts2-010crm_sc-ioc-920/st.cmd
)

