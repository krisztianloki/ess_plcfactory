from __future__ import absolute_import
from __future__ import print_function

import filecmp
import os
import shutil
import tempfile
import unittest

import helpers
from plcfactory import IOC


class FakeDevice(object):
    def __init__(self, name, typ, controlledBy = [], externalLinks = [], properties = {}):
        super(FakeDevice, self).__init__()

        self._name = name
        self._type = typ
        self._controlledBy = controlledBy
        self._externalLinks = externalLinks
        self._properties = properties


    def name(self):
        return self._name


    def deviceType(self):
        return self._type


    def controlledBy(self, **kw):
        return self._controlledBy


    def externalLinks(self, **kw):
        return self._externalLinks


    def properties(self, **kw):
        return self._properties



class FakeE3(object):
    def __init__(self, iocsh):
        super(FakeE3, self).__init__()

        self._iocsh = iocsh


    def iocsh(self):
        return self._iocsh



class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        if type is None:
            shutil.rmtree(self.dirpath)



class TestIOC(unittest.TestCase):
    def setUp(self):
        self.device = FakeDevice("Fake", "IOC", properties = {'EPICSVersion': "7.0.5", 'E3RequireVersion': "3.4.1"})


    def tearDown(self):
        pass


    def filecmp(self, first, second, **kw):
        with open(first, "rt") as f:
            first_lines = f.readlines()
        with open(second, "rt") as s:
            second_lines = s.readlines()

        # Remove empty lines
        first_lines = list(filter(lambda x: True if x.strip() else False, first_lines))
        second_lines = list(filter(lambda x: True if x.strip() else False, second_lines))

        return first_lines == second_lines

    def _master_env_sh(self, directory, iocname = None, iocdir = None, extra_before_lines = [], extra_after_lines = [], extra_spaces = ""):
        master_env_sh = os.path.join(directory, "master_env.sh")
        if iocname is None:
            iocname = self.device.name()
        if iocdir is None:
            iocdir = helpers.sanitizeFilename(iocname)
        with open(master_env_sh, "wt") as env_sh:
            env_sh.writelines(extra_before_lines)
            print('export IOCNAME="{}"'.format(iocname), file = env_sh)
            print('{es}export IOCDIR{es}={es}"{id}"{es}'.format(es = extra_spaces, id = iocdir), file = env_sh)
            env_sh.writelines(extra_after_lines)

        return master_env_sh


    def test_env_sh(self):
        ioc = IOC(self.device)
        with mkdtemp() as ioc_dir:
            # Check with no env.sh
            master_env_sh = self._master_env_sh(ioc_dir)
            ioc._IOC__create_env_sh(ioc_dir, "1.0.0")
            env_sh = os.path.join(ioc_dir, "env.sh")
            self.assertTrue(self.filecmp(master_env_sh, env_sh))

            # Check with env.sh having extra spaces in funny places
            master_env_sh = self._master_env_sh(ioc_dir, extra_spaces = "   ")
            shutil.copyfile(master_env_sh, env_sh)
            master_env_sh = self._master_env_sh(ioc_dir)
            ioc._IOC__create_env_sh(ioc_dir, "1.0.0")
            env_sh = os.path.join(ioc_dir, "env.sh")
            self.assertTrue(self.filecmp(master_env_sh, env_sh))

            # Check with env.sh containing extra variables, and lines
            extra_before_lines = []
            extra_before_lines.append("# This is a comment that should be preserved\n")
            extra_before_lines.append('export IOCDIR="will_be_overriden"\n')
            extra_after_lines = []
            extra_after_lines.append('export FLY_MY="pretties"\n')
            master_env_sh = self._master_env_sh(ioc_dir, iocname = "my-ioc-name", extra_before_lines = extra_before_lines, extra_after_lines = extra_after_lines)
            shutil.copyfile(master_env_sh, env_sh)
            self._master_env_sh(ioc_dir, extra_before_lines = extra_before_lines, extra_after_lines = extra_after_lines)
            ioc._IOC__create_env_sh(ioc_dir, "1.0.0")
            self.assertTrue(self.filecmp(master_env_sh, env_sh))


    def test_st_cmd(self):
        ioc = IOC(self.device)
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp() as ioc_dir:
            st_cmd = os.path.join(ioc_dir, "st.cmd")
            master_st_cmd = os.path.join(ioc_dir, "master_st.cmd")

            #
            # Check with no st.cmd
            #
            with open(master_st_cmd, "wt") as mst:
                print("""# Startup for {iocname}

# Load standard IOC startup scripts
require essioc
iocshLoad("$(essioc_DIR)/common_config.iocsh")

# Register our db directory
epicsEnvSet(EPICS_DB_INCLUDE_PATH, "$(E3_CMD_TOP)/db:$(EPICS_DB_INCLUDE_PATH=.)")

# Load PLC specific startup script
iocshLoad("$(E3_CMD_TOP)/iocsh/{iocsh}")""".format(iocname = ioc.name(), iocsh = ioc._e3.iocsh()), file = mst)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))

            #
            # Check with an unmodified st.cmd
            #
            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))

            #
            # Check with an st.cmd without $(E3_CMD_TOP)
            #
            with open(st_cmd, "wt") as st:
                print("""# Startup for {iocname}

# Load standard IOC startup scripts
require essioc
iocshLoad("$(essioc_DIR)/common_config.iocsh")

# Register our db directory
epicsEnvSet(EPICS_DB_INCLUDE_PATH, "$(E3_CMD_TOP)/db:$(EPICS_DB_INCLUDE_PATH=.)")

# Load PLC specific startup script
iocshLoad("iocsh/{iocsh}")""".format(iocname = ioc.name(), iocsh = ioc._e3.iocsh()), file = st)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))

            #
            # Check with a custom st.cmd (only requires in custom st.cmd)
            #
            with open(master_st_cmd, "wt") as mst:
                # This should be the result
                print("""# Startup for {iocname}

require my_shiny_module
require essioc

# Load standard IOC startup scripts
iocshLoad("$(essioc_DIR)/common_config.iocsh")

# Register our db directory
epicsEnvSet(EPICS_DB_INCLUDE_PATH, "$(E3_CMD_TOP)/db:$(EPICS_DB_INCLUDE_PATH=.)")

# Load PLC specific startup script
iocshLoad("$(E3_CMD_TOP)/iocsh/{iocsh}")""".format(iocname = ioc.name(), iocsh = ioc._e3.iocsh()), file = mst)

            with open(st_cmd, "wt") as st:
                # This is the initial st.cmd
                print("""
require my_shiny_module
require essioc
""", file = st)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))

            #
            # Check with a custom st.cmd (push the limits with this custom st.cmd)
            #
            with open(master_st_cmd, "wt") as mst:
                # This should be the result
                print("""# Startup for {iocname}

# We should iocshLoad("$(essioc_DIR)/common_config.iocsh")
epicsEnvSet(foo, "bar") # We should iocshLoad("$(essioc_DIR)/common_config.iocsh")
iocshLoad("my_iocsh.iocsh")
# Register our db directory
epicsEnvSet(EPICS_DB_INCLUDE_PATH, "$(E3_CMD_TOP)/db:$(EPICS_DB_INCLUDE_PATH=.)")
iocshLoad("$(E3_CMD_TOP)/iocsh/{iocsh}")

# Load PLC specific startup script
#iocshLoad("iocsh/{iocsh}")

# Load standard IOC startup scripts
require essioc
iocshLoad("$(essioc_DIR)/common_config.iocsh")
""".format(iocname = ioc.name(), iocsh = ioc._e3.iocsh()), file = mst)

            with open(st_cmd, "wt") as st:
                # This is the initial st.cmd
                print("""# We should iocshLoad("$(essioc_DIR)/common_config.iocsh")
epicsEnvSet(foo, "bar") # We should iocshLoad("$(essioc_DIR)/common_config.iocsh")
iocshLoad("my_iocsh.iocsh")
iocshLoad("iocsh/{iocsh}")

# Load PLC specific startup script
#iocshLoad("iocsh/{iocsh}")
""".format(iocsh = ioc._e3.iocsh()), file = st)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))



if __name__ == "__main__":
    unittest.main()
