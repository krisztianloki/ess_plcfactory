#
#  Copyright (c) 2018 - Present  European Spallation Source ERIC
#
#  The program is free software: you can redistribute
#  it and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 2 of the
#  License, or any newer version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program. If not, see https://www.gnu.org/licenses/gpl-2.0.txt
#
#
# Author  : Krisztian Loki
# email   : krisztian.loki@esss.se
# Date    : generated by 2018Oct27-1524-31CEST
# version : 0.0.0
#

## The following lines are mandatory, please don't change them.
where_am_I := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
include $(E3_REQUIRE_TOOLS)/driver.makefile
include $(where_am_I)/../configure/DECOUPLE_FLAGS


TEMPLATES += $(wildcard db/*.db)
SCRIPTS   += $(wildcard iocsh/*.iocsh)

REQUIRED=opcua

ifneq ($(strip $(OPCUA_DEP_VERSION)),)
opcua_VERSION=$(OPCUA_DEP_VERSION)
endif


## This RULE should be used in case of inflating DB files
## db rule is the default in RULES_DB, so add the empty one
## Please look at e3-mrfioc2 for example.

db:

.PHONY: db

vlibs:

.PHONY: vlibs