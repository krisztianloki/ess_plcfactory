""" PLC Factory: Global variables """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"

# global dictionaries for memoization
# templates as well as device information is only requested
# at most one time

# all devices and their properties
# key: device, value: dict of all properties/values
deviceDict   = dict()

# same, but for backtracking
# (leads to a conceptually simpler implementation)
cached       = dict()

# timestamp for names of output files
timestamp    = None

# md5 hash sum for output file
hashSum      = None

# choose between production (CCDB) and test (CCDB-test)
production = True