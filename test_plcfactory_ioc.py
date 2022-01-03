from __future__ import absolute_import
from __future__ import print_function

import argparse
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


    def _ioc_args(self, generate_st_cmd = True):
        parser = argparse.ArgumentParser(add_help = False)
        IOC.add_parser_args(parser)

        argv = ["--ioc", "--no-ioc-git"]
        if not generate_st_cmd:
            argv.append("--no-ioc-st-cmd")

        return IOC.parse_args(parser.parse_known_args(argv)[0])


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


    def _master_st_cmd(self, directory, ioc):
        master_st_cmd = os.path.join(directory, "master_st.cmd")

        #
        # Check with no st.cmd
        #
        with open(master_st_cmd, "wt") as mst:
            print("""# Startup for {iocname}

# Load required modules
require essioc
require s7plc
require modbus
require calc

# Load standard IOC startup scripts
iocshLoad("$(essioc_DIR)/common_config.iocsh")

# Register our db directory
epicsEnvSet(EPICS_DB_INCLUDE_PATH, "$(E3_CMD_TOP)/db:$(EPICS_DB_INCLUDE_PATH=.)")

# Load PLC specific startup script
iocshLoad("$(E3_CMD_TOP)/iocsh/{iocsh}", "MODVERSION=$(IOCVERSION=$(DEFAULT_PLCIOCVERSION))")""".format(iocname = ioc.name(), iocsh = ioc._e3.iocsh()), file = mst)

        return master_st_cmd


    def _custom_st_cmd(self, directory):
        st_cmd = os.path.join(directory, "st.cmd")

        #
        # Check with a modified st.cmd
        #
        with open(st_cmd, "wt") as st:
            print("""# Startup for me

# Load required modules
require essioc
require me

# Load standard IOC startup scripts
iocshLoad("$(essioc_DIR)/common_config.iocsh")

iocshLoad("me")""", file = st)

        return st_cmd


    def _st_cmd_orig(self, directory):
        return os.path.join(directory, "st.cmd.orig")


    def test_env_sh(self):
        ioc = IOC(self.device, self._ioc_args())
        with mkdtemp(prefix = "test-plcfactory-ioc-env_sh") as ioc_dir:
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


    def test_no_st_cmd(self):
        #
        # Check with no st.cmd
        #
        ioc = IOC(self.device, self._ioc_args())
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-no-st_cmd") as ioc_dir:
            st_cmd = os.path.join(ioc_dir, "st.cmd")
            master_st_cmd = self._master_st_cmd(ioc_dir, ioc)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))


    def test_no_st_cmd_dont_generate(self):
        #
        # Check with no st.cmd and --no-ioc-st-cmd
        #
        ioc = IOC(self.device, self._ioc_args(False))
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-no-st_cmd-dont-generate") as ioc_dir:
            st_cmd = os.path.join(ioc_dir, "st.cmd")
            master_st_cmd = self._master_st_cmd(ioc_dir, ioc)

            ioc._IOC__create_st_cmd(ioc_dir)
            # st.cmd should be generated even with `--no-ioc-st-cmd`
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))


    def test_unmodified_st_cmd(self):
        #
        # Check with an unmodified st.cmd
        #
        ioc = IOC(self.device, self._ioc_args())
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-unmodified-st_cmd") as ioc_dir:
            st_cmd = os.path.join(ioc_dir, "st.cmd")
            master_st_cmd = self._master_st_cmd(ioc_dir, ioc)

            shutil.copy(master_st_cmd, st_cmd)
            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))
            self.assertFalse(os.path.exists(self._st_cmd_orig(ioc_dir)))


    def test_unmodified_st_cmd_dont_generate(self):
        #
        # Check with an unmodified st.cmd and --no-ioc-st-cmd
        #
        ioc = IOC(self.device, self._ioc_args(False))
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-unmodified-st_cmd-dont-generate") as ioc_dir:
            st_cmd = os.path.join(ioc_dir, "st.cmd")
            master_st_cmd = self._master_st_cmd(ioc_dir, ioc)

            shutil.copy(master_st_cmd, st_cmd)
            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))
            self.assertFalse(os.path.exists(self._st_cmd_orig(ioc_dir)))


    def test_modified_st_cmd(self):
        #
        # Check with a modified st.cmd
        #
        ioc = IOC(self.device, self._ioc_args())
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-modified-st_cmd") as ioc_dir:
            master_st_cmd = self._master_st_cmd(ioc_dir, ioc)

            st_cmd = self._custom_st_cmd(ioc_dir)
            custom_st_cmd = os.path.join(ioc_dir, "custom-st.cmd")
            shutil.copy(st_cmd, custom_st_cmd)

            with open(self._st_cmd_orig(ioc_dir), "wt") as f:
                print("Should be overwritten", file = f)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(master_st_cmd, st_cmd))
            self.assertTrue(self.filecmp(custom_st_cmd, self._st_cmd_orig(ioc_dir)))


    def test_modified_st_cmd_dont_generate(self):
        #
        # Check with a modified st.cmd and --no-ioc-st-cmd
        #
        ioc = IOC(self.device, self._ioc_args(False))
        ioc._e3 = FakeE3("myplc.iocsh")
        with mkdtemp(prefix = "test-plcfactory-ioc-modified-st_cmd-dont-generate") as ioc_dir:
            st_cmd = self._custom_st_cmd(ioc_dir)
            custom_st_cmd = os.path.join(ioc_dir, "custom-st.cmd")
            shutil.copy(st_cmd, custom_st_cmd)

            ioc._IOC__create_st_cmd(ioc_dir)
            self.assertTrue(self.filecmp(custom_st_cmd, st_cmd))
            self.assertFalse(os.path.exists(self._st_cmd_orig(ioc_dir)))



if __name__ == "__main__":
    unittest.main()
