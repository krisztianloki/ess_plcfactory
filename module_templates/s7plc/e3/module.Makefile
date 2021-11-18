#
#  Copyright (c) 2019 - 2020, European Spallation Source ERIC
#
#  The program is free software: you can redistribute it and/or modify it
#  under the terms of the BSD 3-Clause license.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.
# 
# Author  : Krisztian Loki
# email   : krisztian.loki@esss.se
# Date    : 2020-10-07
# version : 0.0.0
#

## The following lines are mandatory, please don't change them.
where_am_I := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
include $(E3_REQUIRE_TOOLS)/driver.makefile
include $(E3_REQUIRE_CONFIG)/DECOUPLE_FLAGS


############################################################################
#
# Required modules
#
############################################################################

# These are required for the communication and EPICS db
REQUIRED += modbus s7plc calc

ifneq ($(strip $(CALC_DEP_VERSION)),)
calc_VERSION=$(CALC_DEP_VERSION)
endif

ifneq ($(strip $(MODBUS_DEP_VERSION)),)
modbus_VERSION=$(MODBUS_DEP_VERSION)
endif

ifneq ($(strip $(S7PLC_DEP_VERSION)),)
s7plc_VERSION=$(S7PLC_DEP_VERSION)
endif


############################################################################
#
# Exclude non-linux-x86_64 architectures
#
############################################################################

EXCLUDE_ARCHS += linux-ppc64e6500 corei7-poky
ARCH_FILTER = linux-x86_64


############################################################################
#
# .db files that should be copied to $(module)/Db
#
############################################################################

TEMPLATES += $(wildcard db/*.db)


############################################################################
#
# Startup scripts that should be installed in the base directory
#
############################################################################

SCRIPTS += $(wildcard iocsh/*.iocsh)



vlibs:

.PHONY: vlibs
