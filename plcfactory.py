#!/usr/bin/env python2
# vim: set fileencoding=utf-8 :

from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Entry point """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__credits__    = [ "Gregor Ulm",
                   "David Brodrick",
                   "Nick Levchenko",
                   "Francois Bellorini",
                   "Ricardo Fernandes"
                 ]
__license__    = "GPLv3"
__maintainer__ = "Krisztián Löki"
__email__      = "krisztian.loki@ess.eu"
__status__     = "Production"
__env__        = "Python version 2.7"
__product__    = "ics_plc_factory"

# Python libraries
import sys
if sys.version_info.major != 2:
    raise RuntimeError("""
PLCFactory supports Python-2.x only. You are running {}
""".format(sys.version))

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
import argparse
import datetime
import filecmp
import os
import time
import hashlib
import zlib
from shutil import copy2
from ast import literal_eval as ast_literal_eval

import plcf_git as git


tainted = False
master_branch = True


def taint_message():
    ret = False
    if not master_branch:
        ret = True
        print("""
+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+
* You are not on branch 'master'; warranty is void. *
+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+
""", file = sys.stderr)

    if tainted:
        ret = True
        print("""
+++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Your working copy is not clean; warranty is void. +
+++++++++++++++++++++++++++++++++++++++++++++++++++++
""", file = sys.stderr)

    return ret


if git.get_status() is False:
    tainted = True

if git.get_current_branch() != "master":
    master_branch = False


taint_message()

# Template Factory
parent_dir = os.path.abspath(os.path.dirname(__file__))
tf_dir     = os.path.join(parent_dir, 'template_factory')
sys.path.append(tf_dir)
del tf_dir

from tf_ifdef import IF_DEF

try:
    import tf
except AttributeError as e:
    if e.args[0] == "'module' object has no attribute 'iglob'":
        # glob.py has been renamed to plcf_glob.py but the .pyc can still be
        # there. Remove the .pyc and reload glob and try to import tf again
        os.unlink(os.path.join(parent_dir, "glob.pyc"))
        import glob
        from imp import reload as imp_reload
        imp_reload(glob)
        del glob
        del imp_reload

        import tf
    else:
        raise

del parent_dir


# PLC Factory modules
import plcf_glob as glob
import plcf
from plcf_ext import PLCFExtException
from cc import CC
import helpers


# global variables
OUTPUT_DIR      = "output"
MODULES_DIR     = os.path.join(os.path.dirname(__file__), "module_templates")
TEMPLATE_TAG    = "TEMPLATE"
HEADER_TAG      = "HEADER"
FOOTER_TAG      = "FOOTER"
IFDEF_EXTENSION = ".def"
hashobj         = None
ifdefs          = dict()
printers        = dict()
ifdef_params    = dict(PLC_TYPE = "SIEMENS")
plcfs           = dict()
output_files    = dict()
previous_files  = None
device_tag      = None
epi_version     = None
hashes          = dict()
prev_hashes     = None
generate_ioc    = False
ioc             = None
e3              = None
branch          = git.get_current_branch()
commit_id       = git.get_local_ref(branch)
if commit_id is not None:
    ifdef_params["COMMIT_ID"] = commit_id


class PLCFactoryException(Exception):
    status = 1
    def __init__(self, *args):
        super(PLCFactoryException, self).__init__(*args)
        try:
            self.message = args[0]
        except IndexError:
            self.message = ""


    def __str__(self):
        if self.message is not None:
            return """
{banner}
{msg}
{banner}
""".format(banner = "*" * max(map(lambda x: len(x), self.message.splitlines())), msg = self.message)
        else:
            return super(PLCFactoryException, self).__str__()



class ProcessTemplateException(PLCFactoryException):
    def __init__(self, device, template, exception, *args):
        super(ProcessTemplateException, self).__init__(*args)
        self.device    = device
        self.template  = template
        self.exception = exception
        self.message = """The following exception occured during the processing of template '{template}' of device '{device}':
{exc}: {msg}""".format(template = self.template,
                       device   = self.device,
                       exc      = type(self.exception).__name__,
                       msg      = self.exception)



class Hasher(object):
    def __init__(self, hash_base = None):
        self._hashobj = hashlib.sha256(hash_base.encode())


    def update(self, string):
        try:
            self._hashobj.update(string.encode())
        except UnicodeDecodeError:
            # Happens on Py2 with strings containing unicode characters
            self._hashobj.update(string)


    def _crc32(self):
        return zlib.crc32(self._hashobj.hexdigest().encode())


    def getHash(self):
        return self._hashobj.hexdigest()


    def getCRC32(self):
        crc32 = self._crc32()
        # Python3 returns an UNSIGNED integer. But we need a signed integer
        if crc32 > 0x7FFFFFFF:
            return str(crc32 - 0x100000000)

        return str(crc32)



class E3(object):
    def __init__(self, modname, snippet = None):
        super(E3, self).__init__()

        if snippet is None:
            modname = helpers.sanitizeFilename(modname.lower())

        if modname.startswith('e3-'):
            modname = modname[len('e3-'):]

        self._modulename = modname.replace('-', '_')
        self._snippet    = snippet.replace('-', '_') if snippet is not None else self._modulename

        self._files = []
        self._test_cmd = False

        glob.e3_modulename = self._modulename
        glob.e3_snippet    = self._snippet


    def modulename(self):
        """
        Returns the name of the module without the 'e3-' prefix
        """
        return self._modulename


    def snippet(self):
        """
        Returns the name of the .iocsh snippet
        """
        return self._snippet


    def files(self):
        """
        Returns the list of files that are in the module
        """
        return self._files


    def iocsh_printer(self):
        """
        Returns the printer that generated the iocsh snippet
        """
        return  printers[self._startup]


    @staticmethod
    def from_device(device):
        """
        Create an E3 object from the EPICSModule and EPICSSnippet properties of 'device'
        """

        dev_props = device.properties()
        modulename = dev_props.get("EPICSModule", [])
        if len(modulename) == 1:
            modulename = modulename[0]
            if modulename != helpers.sanitizeFilename(modulename):
                print("Overriding modulename because it is not a valid filename", file = sys.stderr)
        else:
            print("Ignoring EPICSModule property; it is an array", file = sys.stderr)
            modulename = deviceName.lower()

        modulename = helpers.sanitizeFilename(modulename)

        snippet = dev_props.get("EPICSSnippet", [])
        if len(snippet) == 1:
            snippet = snippet[0]
            validSnippet = helpers.sanitizeFilename(snippet)
            if snippet != validSnippet:
                print("Overriding snippet because it is not a valid filename", file = sys.stderr)
                snippet = validSnippet
        else:
            print("Ignoring EPICSSnippet property; it is an array", file = sys.stderr)
            snippet = modulename

        return E3(modulename, snippet)


    def copy_files(self, basedir):
        """
        Create the directory structure and copy the generated files
        """
        ch = copy_helper(basedir)

        #
        # Copy files
        #
        ch.m_cp(output_files.get('EPICS-DB', output_files.get('EPICS-OPC-DB')), "db", self.modulename() + ".db")

        try:
            ch.m_cp(output_files['EPICS-TEST-DB'],           "db",      self.modulename() + "-test.db")
        except KeyError:
            pass

        try:
            self._startup = 'AUTOSAVE-IOCSH'
            ch.m_cp(output_files[self._startup],                   "iocsh",   self.snippet() + ".iocsh")
        except KeyError:
            self._startup = 'IOCSH'
            ch.m_cp(output_files[self._startup],                   "iocsh",   self.snippet() + ".iocsh")

        self._test_cmd = True
        try:
            test_startup = 'AUTOSAVE-TEST-IOCSH'
            ch.m_cp(output_files[test_startup],              "iocsh",   self.snippet() + "-test.iocsh")
        except KeyError:
            try:
                test_startup = 'TEST-IOCSH'
                ch.m_cp(output_files[test_startup],          "iocsh",   self.snippet() + "-test.iocsh")
            except KeyError:
                self._test_cmd = False

        ch.m_cp(output_files["CREATOR"],                     "misc",    "creator")
        ch.m_cp(output_files["DEVICE-LIST"],                 "misc",    "device-list.txt")

        try:
            ch.m_cp(output_files["BECKHOFF"],                "misc",    os.path.basename(output_files["BECKHOFF"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["STANDARD_SCL"],            "misc",    os.path.basename(output_files["STANDARD_SCL"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["PROJECT_SCL"],             "misc",    os.path.basename(output_files["PROJECT_SCL"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["ARCHIVE"],                 "misc",    self.modulename() + ".archive")
        except KeyError:
            pass

        #
        # Copy CCDB dump
        #
        if output_files['CCDB-DUMP'] is not None:
            miscdir = os.path.join(basedir, "misc")
            try:
                import zipfile
                with zipfile.ZipFile(output_files['CCDB-DUMP'], "r") as z:
                    z.extractall(miscdir)
                    self._files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
                    z.close()
            except:
                helpers.rmdirs(os.path.join(miscdir, "ccdb"))
                print("Cannot copy CCDB dump to E3 module", file = sys.stderr)

        #
        # Copy the README file to the modname directory
        #
        readme = os.path.join(basedir, "README.md")
        copy2(output_files["README"], readme)
        self._files.append(readme)

        self._files.extend(ch.copied())

        return self._files


    def create(self):
        """
        Create the E3 module and some helper scripts to run it
        """
        out_mdir = os.path.join(OUTPUT_DIR, "modules", "-".join([ "e3", self.modulename() ]))
        helpers.makedirs(out_mdir)

        self._files.extend(m_copytree(module_dir("e3"), out_mdir))

        out_sdir = os.path.join(out_mdir, self.modulename())
        helpers.makedirs(out_sdir)
        self.copy_files(out_sdir)

        output_files['E3'] = self._files

        iocsh_printer   = self.iocsh_printer()
        macro_list      = iocsh_printer.macros()
        if macro_list:
            macros      = ", ".join(["{m}={m}".format(m = iocsh_printer.macro_name(macro)) for macro in macro_list])
            live_macros = ", {}".format(macros)
        else:
            macros      = ""
            live_macros = ""

        #
        # Create env.sh
        #
        with open(os.path.join(OUTPUT_DIR, "env.sh"), "w") as run:
            print("""IOCNAME='{modulename}'""".format(modulename = self.modulename()), file = run)

        #
        # Create script to run module with 'safe' defaults
        #
        with open(os.path.join(OUTPUT_DIR, "run_module.bash"), "w") as run:
            iocsh_bash = """iocsh.bash -l {moduledir}/cellMods -r {modulename},plcfactory -c 'iocshLoad($({modulename}_DIR)/{snippet}.iocsh, "IPADDR = 127.0.0.1, """.format(moduledir  = os.path.abspath(out_mdir),
                                                                                                                                                                             modulename = self.modulename(),
                                                                                                                                                                             snippet    = self.snippet())
            if 'OPC' in ifdef_params['PLC_TYPE']:
                print(iocsh_bash + """PORT = 4840, PUBLISHING_INTERVAL = 200{macros}")'""".format(macros = live_macros), file = run)
            else:
                print(iocsh_bash + """ RECVTIMEOUT = 3000{macros}")'""".format(macros = live_macros), file = run)

        if self._test_cmd:
            #
            # Create script to run test version of module
            #
            with open(os.path.join(OUTPUT_DIR, "run_test_module.bash"), "w") as run:
                if macros:
                    test_macros = ', "{}"'.format(macros)
                else:
                    test_macros = ""
                print("""iocsh.bash -l {moduledir}/cellMods -r {modulename},plcfactory -c 'iocshLoad($({modulename}_DIR)/{snippet}-test.iocsh, "_={macros}")'""".format(moduledir  = os.path.abspath(out_mdir),
                                                                                                                                                                        modulename = self.modulename(),
                                                                                                                                                                        snippet    = self.snippet(),
                                                                                                                                                                        macros     = test_macros), file = run)

        print("E3 Module created:", out_mdir)
        return out_mdir



class IOC(object):
    def __init__(self, device):
        super(IOC, self).__init__()

        # Store the name of the PLC
        self._plc = device.name()

        # Create our own E3 module
        self._e3 = E3(self._plc)

        ioc = self.__get_ioc(device)
        self._name = ioc.name()
        self._dir = helpers.sanitizeFilename(self._name.lower()).replace('-', '_')
        self._repo = get_e3_repository(ioc)
        if self._repo:
            self._dir = helpers.url_to_path(self._repo).split('/')[-1]
            if self._dir.endswith('.git'):
                self._dir = self._dir[:-4]
            else:
                self._repo += ".git"


    def __get_ioc(self, device):
        """
        Get the IOC that _directly_ controls 'device'
        """
        for c in device.controlledBy(convert = False):
            if c.deviceType() == 'IOC':
                return c

        raise PLCFactoryException("Could not find IOC for {}".format(device.name()))


    def plc(self):
        """
        Returns the PLC name this IOC controls
        """
        return self._plc


    def name(self):
        """
        Returns the IOC name
        """
        return self._name


    def directory(self):
        """
        Returns the directory name (as derived from repo URL or name) where the IOC is generated
        """
        return self._dir


    def repo(self):
        """
        Returns the IOC repository URL
        """
        return self._repo


    def create(self, version):
        """
        Generate IOC
        """

        out_idir = os.path.join(OUTPUT_DIR, "ioc", self.directory())
        out_idir = os.path.join("/tmp/plcfactory", "ioc", self.directory())
        helpers.makedirs(out_idir)
        if self.repo():
            # Cannot specify 'branch = "master"'; git segfaults when trying to clone an empty repository and checking out its "master" branch
            # Update the master branch if available
            repo = git.GIT.clone(self.repo(), out_idir, update = True)
            try:
                repo.create_branch(glob.timestamp, "master")
            except git.GITException:
                # Create a .gitignore file on 'master' so we can create a development branch
                gitignore = os.path.join(out_idir, ".gitignore")
                with open(gitignore, "wt") as gf:
                    pass
                repo.add(gitignore)
                repo.commit("Initialized repository")
                repo.push()
                # Now that we have a proper 'master' branch we can try creating a development branch
                repo.create_branch(glob.timestamp, "master")
        else:
            repo = None

        # Copy the generated e3 files
        self._e3.copy_files(out_idir)

        # Create env.sh
        env_sh = os.path.join(out_idir, 'env.sh')
        with open(env_sh, 'wt') as f_env_sh:
            print('export IOCNAME={}'.format(self.name()), file = f_env_sh)
            print('export EPICS_DB_INCLUDE_PATH="`pwd`/db"', file = f_env_sh)
            print('export {}_VERSION={}'.format(self._e3.modulename(), version if version else 'plcfactory@' + glob.timestamp), file = f_env_sh)

        # Create st.cmd
        st_cmd = os.path.join(out_idir, 'st.cmd')
        with open(st_cmd, 'wt') as f_st_cmd:
            print("""# Startup for {}
require modbus
require s7plc
require calc""".format(self.name()), file = f_st_cmd)
            print("""
require autosave
require recsync""", file = f_st_cmd)
            print("""
iocshLoad(iocsh/{}.iocsh)""".format(self._e3.snippet()), file = f_st_cmd)

        if self._e3.iocsh_printer().hostname() is None:
            raise PLCFactoryException("Hostname of the PLC is not specified, generated IOC is not usable!")

        # Update the repository
        if repo:
            repo.add(self._e3.files())
            self.__remove_stale_files(repo, self._e3.files())
            repo.add([env_sh, st_cmd])
            repo.commit()
            if version:
                repo.tag(version, override_local = True)
                link = repo.push()
                if link:
                    helpers.xdg_open(link)


    def __remove_stale_files(self, repo, current_files):
        # Get the 'toplevel' directories E3 creates
        paths = set()
        for cf in current_files:
            # Get a repository relative path
            relpath = os.path.relpath(cf, repo.path())
            # Get the first component
            path = Path(relpath)
            path = path.parts[0]
            # Make sure that it is a directory
            if not os.path.isdir(os.path.join(repo.path(), path)):
                continue
            paths.add(path)

        # Now check that every file under 'paths' is still relevant
        for path in paths:
            for root, dirs, files in os.walk(os.path.join(repo.path(), path)):
                for f in files:
                    if os.path.join(root, f) not in current_files:
                        repo.remove(os.path.join(root, f))



def initializeHash(hash_base = None):
    return Hasher(hash_base)


def openHeaderFooter(device, tag, templateID):
    assert isinstance(tag,        str)
    assert isinstance(templateID, str)

    artifact = device.downloadArtifact(extension = ".txt",
                                       filetype = "{} for {}".format("_".join([ tag, TEMPLATE_TAG, templateID ]), templateID),
                                       custom_filter = matchingArtifact,
                                       filter_args = ((tag, TEMPLATE_TAG), templateID))

    if not artifact:
        return []

    with open(artifact.saved_as()) as f:
        lines = f.readlines()

    return lines


def downloadTemplate(device, templateID):
    assert isinstance(templateID, str)

    artifact = device.downloadArtifact(extension = ".txt",
                                       filetype = "{} for {}".format("_".join([ TEMPLATE_TAG, templateID ]), templateID),
                                       custom_filter = matchingArtifact,
                                       filter_args = (TEMPLATE_TAG, templateID))

    if artifact is not None:
        return artifact.saved_as()

    return None


def matchingArtifact(artifact, tag, templateID):
    filename = artifact.filename()

    # exactly one '.' in filename
    if filename.count('.') != 1:
        return False

    assert isinstance(templateID, str)
    if isinstance(tag, tuple):
        assert len(tag) == 2
        assert isinstance(tag[0], str)
        assert isinstance(tag[1], str)

        match  = "{}.txt".format("_".join([ tag[0], tag[1], templateID ]))
    else:
        assert isinstance(tag, str)

        # do not match HEADERs and FOOTERs if not in HEADER/FOOTER mode
        if HEADER_TAG in filename or FOOTER_TAG in filename:
            return False
        match  = "{}.txt".format("_".join([ tag, templateID ]))

    return filename.endswith(match)


def createFilename(cplcf, header):
    assert isinstance(header, list)

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if tagPos == -1:
        header = [ '{} [PLCF#RAW_INSTALLATION_SLOT]_[PLCF#DEVICE_TYPE]-[PLCF#TEMPLATE]_[PLCF#TIMESTAMP].scl'.format(tag) ]
        tagPos = 0

    filename = header[tagPos]

    # remove tag and strip surrounding whitespace
    filename = filename[len(tag):].strip()
    filename = cplcf.process(filename)

    return helpers.sanitizeFilename(filename)


def findTag(lines, tag):
    tagPos = -1

    if not lines:
        return tagPos

    assert isinstance(lines, list)
    assert isinstance(tag,   str)

    for i in range(len(lines)):
        if lines[i].startswith(tag):
            tagPos = i
            break

    return tagPos


def processHash(header):
    assert isinstance(header, list)

    tag     = "#HASH"
    pos     = -1

    for i in range(len(header)):
        if tag in header[i]:
            pos = i
            hashSum     = hashobj.getCRC32()
            line        = header[pos]
            tagPos      = line.find(tag)
            line        = line[:tagPos] + hashSum + line[tagPos + len(tag):]
            header[pos] = line

    return header


def getEOL(header):
    assert isinstance(header, list)

    tag    = "#EOL"
    tagPos = findTag(header, tag)

    if tagPos == -1:
        return "\n"

    # this really is a quick and dirty hack
    # should be replaced by something like
    # #EOL CR LF
    return header[tagPos][len(tag):].strip().replace('\\n', '\n').replace('\\r', '\r').strip('"').strip("'")


#
# Returns an interface definition object
#
def getIfDef(device):
    # If a definition file is already downloaded (and parsed) for this device then we must use that one
    try:
        return ifdefs[device.name()]
    except KeyError:
        pass

    artifact = device.downloadArtifact(IFDEF_EXTENSION, device_tag, filetype = "Interface Definition")
    if artifact is None:
        # No 'file' artifact found, let's see if there is a URL
        artifact = device.downloadExternalLink("EPI", IFDEF_EXTENSION, device_tag, "Interface Definition", git_tag = epi_version)
        if artifact is None:
            # No def file is present, do not check again
            ifdefs[device.name()] = None
            return None

    # If a definition file is already downloaded and parsed then we just use that one
    try:
        ifdef = ifdefs[artifact]
        ifdefs[device.name()] = ifdef

        return ifdef
    except KeyError:
        pass

    ifdef = IF_DEF.parse(artifact, **ifdef_params)

    if ifdef is not None:
        ifdefs[artifact] = ifdef
        ifdefs[device.name()] = ifdef

    return ifdef


def getHeader(device, templateID, plcf):
    assert isinstance(templateID, str)

    try:
        templatePrinter = printers[templateID]
    except KeyError:
        templatePrinter = tf.get_printer(templateID)

    if templatePrinter is not None:
        print("Using built-in template header")
        printers[templateID] = templatePrinter
        header = []
        templatePrinter.header(header, ROOT_DEVICE = device, PLCF = plcf, OUTPUT_DIR = OUTPUT_DIR, HELPERS = helpers, **ifdef_params)
    else:
        header = openHeaderFooter(device, HEADER_TAG, templateID)

    if not header:
        print("No header found.\n")
    else:
        print("Header read.\n")

    return (header, templatePrinter)


def getFooter(device, templateID, plcf):
    try:
        templatePrinter = printers[templateID]
    except KeyError:
        return openHeaderFooter(device, FOOTER_TAG, templateID)

    print("Using built-in template footer")
    footer = []
    templatePrinter.footer(footer, PLCF = plcf)

    return footer


def getPLCF(device):
    global plcfs

    device_name = device.name()
    try:
        return plcfs[device_name]
    except KeyError:
        cplcf = plcf.PLCF(device)
        plcfs[device_name] = cplcf
        return cplcf


def processTemplateID(templateID, devices):
    assert isinstance(templateID, str)
    assert isinstance(devices,    list)

    start_time = time.time()

    rootDevice = devices[0]
    rcplcf     = getPLCF(rootDevice)
    rcplcf.register_template(templateID)

    if device_tag:
        tagged_templateID = "_".join([ device_tag, templateID ])
    else:
        tagged_templateID = templateID

    print("#" * 60)
    print("Template ID " + tagged_templateID)
    print("Device at root: " + str(rootDevice) + "\n")

    # collect lines to be written at the end
    output = []

    # process header
    (header, templatePrinter) = getHeader(rootDevice, templateID, rcplcf)
    # has to acquire filename _before_ processing the header
    # there are some special tags that are only valid in the header
    outputFile = os.path.join(OUTPUT_DIR, createFilename(rcplcf, header))

    if header:
        header = rcplcf.process(header)

    print("Processing entire tree of controls-relationships:\n")

    can_combine   = tf.is_combinable(templateID)
    def_seen      = None
    template_seen = None

    # for each device, find corresponding template and process it
    output     = []
    for device in devices:
        deviceType = device.deviceType()
        cplcf      = getPLCF(device)
        cplcf.register_template(templateID)

        print(device.name())
        print("Device type: " + deviceType)

        hashobj.update(device.name())

        # get template
        template = None

        # Try to process Interface Definition first
        if templatePrinter is not None:
            ifdef = getIfDef(device)
            if ifdef is not None:
                def_seen = True
                print("Generating template from Definition File...")
                ifdef.calculate_hash(hashobj)
                template = []
                try:
                    templatePrinter.body(ifdef, template, DEVICE = device, PLCF = cplcf)
                except tf.TemplatePrinterException as e:
                    raise ProcessTemplateException(device.name(), templateID, e)

        # Try to download template from artifact
        if template is None:
            template = downloadTemplate(device, "_" + tagged_templateID if device_tag else tagged_templateID)
            if template is not None:
                template_seen = True

        if def_seen and template_seen and not can_combine:
            raise PLCFactoryException("Cannot combine Interface Definitions and ordinary templates with {}".format(templateID))

        # Try to check if we have a default template printer implementation
        if template is None and templatePrinter is not None and not templatePrinter.needs_ifdef():
            print("Using default built-in template...")
            template = []
            try:
                templatePrinter.body(None, template)
            except tf.TemplatePrinterException as e:
                raise ProcessTemplateException(device.name(), templateID, e)

        if template is not None:
            # process template and add result to output
            try:
                if isinstance(template, str):
                    with open(template, 'r') as f:
                        output += cplcf.process(f)
                else:
                    output += cplcf.process(template)
            except (plcf.PLCFException, PLCFExtException) as e:
                raise ProcessTemplateException(device.name(), templateID, e)

            print("Template processed.")

        else:
            print("No template found.")

        print("=" * 40)

    print("\n")

    if not def_seen:
        glob.ccdb.computeHash(hashobj)

    footer = getFooter(rootDevice, templateID, rcplcf)
    if footer:
        footer = rcplcf.process(footer)

    # process #HASH keyword in header and footer
    header      = processHash(header)
    footer      = processHash(footer)

    output      = header + output + footer

    if not output:
        print("There were no templates for ID = {}.\n".format(tagged_templateID))
        return

    # Process counters
    (output, _) = plcf.PLCF.evalCounters(output)

    eol = getEOL(header)
    # write file
    with open(outputFile, 'w') as f:
        for line in output:
            line = line.rstrip()
            if not line.startswith("#COUNTER") \
               and not line.startswith("#FILENAME") \
               and not line.startswith("#EOL"):
                print(line, end = eol, file = f)

    output_files[templateID] = outputFile

    print("Output file written:", outputFile)
    print("Hash sum:", hashobj.getCRC32())
    print("--- %s %.1f seconds ---\n" % (tagged_templateID, time.time() - start_time))


def get_e3_repository(device):
    e3_repo = None

    for e3_repo_link in filter(lambda x: x.name() == 'E3_REPOSITORY', device.externalLinks(convert = False)):
        if e3_repo is None or not e3_repo_link.is_perdevtype():
            e3_repo = e3_repo_link.uri()

    return e3_repo


def processDevice(deviceName, templateIDs):
    assert isinstance(deviceName,  str)
    assert isinstance(templateIDs, list)

    try:
        print("Obtaining controls tree...", end = '', flush = True)
    except TypeError:
        print("Obtaining controls tree...", end = '')
        sys.stdout.flush()

    try:
        device = glob.ccdb.device(deviceName)
    except CC.NoSuchDeviceException:
        print("""
ERROR:
Device '{}' not found.
Please check the list of devices in CCDB, and keep
in mind that device names are case-sensitive.
Maybe you meant one of the following devices:
(Accesing CCDB, may take a few seconds...)""".format(deviceName))
        (filtered, top10) = glob.ccdb.getSimilarDeviceNames(deviceName)
        if not top10:
            print("""
No devices found.""")
        else:
            print("""
Most similar device names in CCDB {}(max. 10):""".format("in chosen slot " if filtered else ""))
            for dev in top10:
                print(dev)

        print("""
Exiting.
""")
        exit(1)

    # Get the EPICSModule and EPICSSnippet properties
    dev_props = device.properties()
    modulename = dev_props.get("EPICSModule", [])
    if len(modulename) == 1:
        modulename = modulename[0]
        if modulename != helpers.sanitizeFilename(modulename):
            print("Overriding modulename because it is not a valid filename")
    else:
        modulename = deviceName.lower()

    modulename = helpers.sanitizeFilename(modulename)

    snippet = dev_props.get("EPICSSnippet", [])
    if len(snippet) == 1:
        snippet = snippet[0]
        validSnippet = helpers.sanitizeFilename(snippet)
        if snippet != validSnippet:
            print("Overriding snippet because it is not a valid filename")
            snippet = validSnippet
    else:
        snippet = modulename

    # Set the module and snippet names from the CCDB properties if needed
    if not glob.eee_modulename:
        glob.eee_modulename = modulename
        glob.eee_snippet    = snippet

    global e3
    if e3 is None:
        e3 = E3.from_device(device)

    if generate_ioc:
        global ioc
        ioc = IOC(device)

    cplcf = getPLCF(device)

    hash_base = """EPICSToPLCDataBlockStartOffset: [PLCF#EPICSToPLCDataBlockStartOffset]
PLCToEPICSDataBlockStartOffset: [PLCF#PLCToEPICSDataBlockStartOffset]
PLC-EPICS-COMMS:Endianness: [PLCF#PLC-EPICS-COMMS:Endianness]"""
    hash_base = "\n".join(cplcf.process(hash_base.splitlines()))

    # create a stable list of controlled devices
    devices = device.buildControlsList(include_self = True, verbose = True)

    hash_per_template = dict()
    for templateID in templateIDs:
        global hashobj
        hashobj = initializeHash(hash_base)

        processTemplateID(templateID, devices)

        hash_per_template[templateID] = (hashobj.getHash(), hashobj.getCRC32())

    # Check if IFA and EPICS-DB hashes are the same and obtain hash for PLC
    try:
        cur_hash = hash_per_template["IFA"]
        if cur_hash[0] != hash_per_template["EPICS-DB"][0]:
            raise PLCFactoryException("Hash mismatch detected between EPICS and PLC. Please file a bug report")
    except KeyError:
        # Fall back to the current hash
        cur_hash = (hashobj.getHash(), hashobj.getCRC32())

    global hashes
    hashes[device.name()] = cur_hash

    try:
        prev_hash = prev_hashes[device.name()]
        # Check if CRC32 is the same but the actual hash is different
        if prev_hash[0] is not None and prev_hash[0] != cur_hash[0] and prev_hash[1] == cur_hash[1]:
            raise PLCFactoryException("CRC32 collision detected. Please file a bug report")
    except (KeyError, TypeError):
        pass

    return device


def create_zipfile(zipit):
    import zipfile

    if not zipit.endswith(".zip"):
        zipit += ".zip"

    zipit = helpers.sanitize_path(zipit)

    z = zipfile.ZipFile(zipit, "w", zipfile.ZIP_DEFLATED)

    tostrip = OUTPUT_DIR + os.path.sep

    def removeoutdir(path):
        try:
            return path[path.index(tostrip) + len(tostrip):]
        except:
            return path

    for f in output_files.itervalues():
        if f is None:
            continue

        if isinstance(f, str):
            z.write(f, removeoutdir(f))
        elif isinstance(f, list):
            for ff in f:
                z.write(ff, removeoutdir(ff))
    z.close()

    print("Zipfile created:", zipit)
    return zipit


def m_copytree(src, dst):
    copied = []
    for name in os.listdir(src):
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)

        if os.path.isdir(srcname):
            helpers.makedirs(dstname)
            copied.extend(m_copytree(srcname, dstname))
        else:
            copied.append(dstname)
            if name == "CONFIG_MODULE":
                with open(srcname, 'r') as src_f:
                    cplcf = plcf.PLCF(None)
                    with open(dstname, 'w') as dst_f:
                        for line in cplcf.process(src_f):
                            print(line, end = '', file = dst_f)
            else:
                copy2(srcname, dstname)

    return copied


def module_dir(module):
    if 'OPC' in ifdef_params["PLC_TYPE"]:
        return os.path.join(MODULES_DIR, "opc", module)

    return os.path.join(MODULES_DIR, "s7plc", module)


class copy_helper(object):
    def __init__(self, basedir):
        super(copy_helper, self).__init__()
        self._basedir = basedir
        self._copied = []


    def __makedir(self, d):
        od = os.path.join(self._basedir, d)
        helpers.makedirs(od)

        return od


    def copied(self):
        return self._copied


    def m_cp(self, src, dest, newname):
        of = os.path.join(self.__makedir(dest), newname)
        copy2(src, of)
        self._copied.append(of)


def create_eee(modulename, snippet):
    eee_files = []
    out_mdir  = os.path.join(OUTPUT_DIR, "modules", "-".join([ "m-epics", modulename ]))
    helpers.makedirs(out_mdir)

    ch = copy_helper(out_mdir)

    eee_files.extend(m_copytree(module_dir("eee"), out_mdir))

    #
    # Copy files
    #
    ch.m_cp(output_files.get('EPICS-DB', output_files.get('EPICS-OPC-DB')), "db", modulename + ".db")

    try:
        ch.m_cp(output_files['EPICS-TEST-DB'],           "db",      modulename + "-test.db")
    except KeyError:
        pass

    try:
        startup = 'AUTOSAVE-ST-CMD'
        ch.m_cp(output_files[startup],                   "startup", snippet + ".cmd")
    except KeyError:
        startup = 'ST-CMD'
        ch.m_cp(output_files[startup],                   "startup", snippet + ".cmd")

    test_cmd = True
    try:
        test_startup = 'AUTOSAVE-ST-TEST-CMD'
        ch.m_cp(output_files[test_startup],              "startup", snippet + "-test.cmd")
    except KeyError:
        try:
            test_startup = 'ST-TEST-CMD'
            ch.m_cp(output_files[test_startup],          "startup", snippet + "-test.cmd")
        except KeyError:
            test_cmd = False

    req_files    = []
    try:
        ch.m_cp(output_files['AUTOSAVE'],                "misc",    modulename + ".req")
        req_files.append(modulename + ".req")
    except KeyError:
        pass

    try:
        ch.m_cp(output_files['AUTOSAVE-TEST'],           "misc",    modulename + "-test.req")
        req_files.append(modulename + "-test.req")
    except KeyError:
        pass

    ch.m_cp(output_files["CREATOR"],                     "misc",    "creator")

    try:
        ch.m_cp(output_files["BECKHOFF"],                "misc",    os.path.basename(output_files["BECKHOFF"]))
    except KeyError:
        pass

    try:
        ch.m_cp(output_files["STANDARD_SCL"],            "misc",    os.path.basename(output_files["STANDARD_SCL"]))
    except KeyError:
        pass

    try:
        ch.m_cp(output_files["PROJECT_SCL"],             "misc",    os.path.basename(output_files["PROJECT_SCL"]))
    except KeyError:
        pass

    #
    # Copy CCDB dump
    #
    if output_files['CCDB-DUMP'] is not None:
        miscdir = os.path.join(out_mdir, "misc")
        try:
            import zipfile
            with zipfile.ZipFile(output_files['CCDB-DUMP'], "r") as z:
                z.extractall(miscdir)
                eee_files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
                z.close()
        except:
            helpers.rmdirs(os.path.join(miscdir, "ccdb"))
            print("Cannot copy CCDB dump to EEE module")

    #
    # Copy the README file to the modname directory
    #
    readme = os.path.join(out_mdir, "PLCFactory.md")
    copy2(output_files["README"], readme)
    eee_files.append(readme)

    #
    # Modify Makefile if needed
    #
    opc = 'OPC' in ifdef_params['PLC_TYPE']
    if opc or req_files:
        with open(os.path.join(out_mdir, "Makefile"), "a") as makefile:
            if opc:
                print("""
USR_DEPENDENCIES += opcua,krisztianloki""", file = makefile)

            if req_files:
                print("""
USR_DEPENDENCIES += autosave
USR_DEPENDENCIES += synappsstd
MISCS += $(wildcard misc/*.req)""", file = makefile)

    eee_files.extend(ch.copied())
    output_files['EEE'] = eee_files

    macros          = ""
    live_macros     = ""
    test_macros     = ""
    startup_printer = printers[startup]
    macro_list      = startup_printer.macros()
    if macro_list:
        macros      = ", ".join(["{m}={m}".format(m = startup_printer.macro_name(macro)) for macro in macro_list])
        live_macros = ", {}".format(macros)

    #
    # Create script to run module with 'safe' defaults
    #
    with open(os.path.join(OUTPUT_DIR, "run_module"), "w") as run:
        if 'OPC' in ifdef_params['PLC_TYPE']:
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}.cmd, "IPADDR=127.0.0.1, PORT=4840, PUBLISHING_INTERVAL=200{macros}")'""".format(modulename = modulename,
                                                                                                                                                              snippet    = snippet,
                                                                                                                                                              macros     = live_macros), file = run)
        else:
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}.cmd, "IPADDR=127.0.0.1, RECVTIMEOUT=3000{macros}")'""".format(modulename = modulename,
                                                                                                                                            snippet    = snippet,
                                                                                                                                            macros     = live_macros), file = run)

    if test_cmd:
        #
        # Create script to run test version of module
        #
        with open(os.path.join(OUTPUT_DIR, "run_test_module"), "w") as run:
            if macros:
                test_macros = ', "{}"'.format(macros)
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}-test.cmd{macros})'""".format(modulename = modulename,
                                                                                                           snippet    = snippet,
                                                                                                           macros     = test_macros), file = run)

    print("EEE Module created:", out_mdir)
    return out_mdir


def read_data_files():
    global hashes
    global prev_hashes

    try:
        with open(os.path.join(helpers.create_data_dir(__product__), "hashes")) as h:
            raw_hashes = h.readline()
    except:
        return

    prev_hashes = ast_literal_eval(raw_hashes)
    import copy
    for (k, v) in prev_hashes.iteritems():
        if isinstance(v, tuple):
            hashes[k] = copy.deepcopy(v)
        else:
            hashes[k] = (None, copy.deepcopy(v))


def write_data_files():
    try:
        with open(os.path.join(helpers.create_data_dir(__product__), "hashes"), 'w') as h:
            print(str(hashes), file = h)
    except:
        print("Was not able to save data files")
        return



def obtain_previous_files():
    global previous_files

    fname = os.path.join(OUTPUT_DIR, ".previous-files")
    try:
        with open(fname, "r") as lf:
            raw_hash       = lf.readline()
            previous_files = ast_literal_eval(raw_hash)
    except:
        return


def create_previous_files():
    fname = os.path.join(OUTPUT_DIR, ".previous-files")
    with open(fname, 'w') as lf:
        print(output_files, file = lf)
        output_files["PREVIOUS_FILES"] = fname


def verify_output(strictness, ignore):
    if strictness == 0 or (previous_files is None and strictness < 3):
        return

    ignored_templates = [ 'PREVIOUS_FILES', 'CREATOR', 'CCDB-DUMP' ]
    ignored_templates.extend(ignore.split(','))
    for template in ignored_templates:
        previous_files.pop(template, None)

    def my_filecmp(f1, f2):
        if filecmp.cmp(f1, f2, shallow = 0):
            return True

        # The files are different, let's try again skipping comment lines
        with open(f1, "r") as fp1, open(f2, "r") as fp2:
            while True:
                l1 = fp1.readline(1024)
                l2 = fp2.readline(1024)

                while l1 and l1[0] == '#':
                    l1 = fp1.readline()

                while l2 and l2[0] == '#':
                    l2 = fp2.readline()

                if l1 != l2:
                    return False

                if not l1:
                    return True

    # Compare files in output_files to those in previous_files
    # previous_files will contain files that are not the same
    # not_checked will contain files that are not found / not generated
    not_checked = dict()
    for (template, output) in output_files.iteritems():
        if template in ignored_templates:
            continue

        try:
            prev = previous_files[template]
        except KeyError:
            not_checked[template] = output
            continue

        # compare prev and output
        try:
            if my_filecmp(prev, output):
                previous_files.pop(template)
        except OSError as e:
            if e.errno == 2:
                not_checked[template] = output
                previous_files.pop(template)
                continue
            raise

    if previous_files:
        print("\n" + "=*" * 40)
        print("""
THE FOLLOWING FILES WERE CHANGED:
""")
        for (template, output) in previous_files.iteritems():
            print("\t{template}:\t{filename}".format(template = template, filename = output))
        print("\n" + "=*" * 40)

        exit(1)

    if not_checked:
        print("\n" + "=*" * 40)
        print("""
THE FOLLOWING FILES WERE NOT CHECKED:
""")
        for (template, output) in not_checked.iteritems():
            print("\t{template}:\t{filename}".format(template = template, filename = output))
        print("\n" + "=*" * 40)

        if strictness > 1:
            # Record last update; even if strict checking was requested
            create_previous_files()

            exit(1)


def record_args(root_device):
    creator = os.path.join(OUTPUT_DIR, createFilename(getPLCF(root_device), ["#FILENAME [PLCF#RAW_INSTALLATION_SLOT]-creator-[PLCF#TIMESTAMP]"]))
    with open(creator, 'w') as f:
        print("""#!/bin/sh

#PLCFactory branch: {branch}
#PLCFactory commit: {commit}
""".format(branch = branch,
           commit = commit_id), file = f)
        print(" ".join(sys.argv), file = f)
    output_files["CREATOR"] = creator


def banner():
    print(" _____  _      _____   ______         _                    ")
    print("|  __ \| |    / ____| |  ____|       | |                   ")
    print("| |__) | |   | |      | |__ __ _  ___| |_ ___  _ __ _   _  ")
    print("|  ___/| |   | |      |  __/ _` |/ __| __/ _ \| '__| | | | ")
    print("| |    | |___| |____  | | ( (_| | (__| |( (_) | |  | |_| | ")
    print("|_|    |______\_____| |_|  \__,_|\___|\__\___/|_|   \__, | ")
    print("                                                     __/ | ")
    print("European Spallation Source, Lund                    |___/ \n")

    taint_message()



class PLCFArgumentError(PLCFactoryException):
    def __init__(self, status, message = None):
        if message is None:
            if isinstance(status, str):
                message = status
                status = 1
        super(PLCFArgumentError, self).__init__(message)
        self.status = status



class PLCFArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        argparse.ArgumentParser.__init__(self)


    def exit(self, status = 0, message = None):
        raise PLCFArgumentError(status, message)



def main(argv):
    def not_empty_string(argument):
        if argument == "":
            raise argparse.ArgumentTypeError("empty string not allowed")
        return argument

    def add_common_parser_args(parser):
        #
        # -d/--device cannot be added to the common args, because it is not a required option in the first pass but a required one in the second pass
        #
        plc_group = parser.add_argument_group("PLC related options")

        plc_args = plc_group.add_mutually_exclusive_group()

        default_tia = "TIAv15.1"

        plc_args.add_argument(
                              '--plc-siemens',
                              '--plc-interface',
                              dest    = "siemens",
                              help    = 'use the default templates for Siemens PLCs and generate interface PLC comms. The default TIA version is {}'.format(default_tia),
                              metavar = 'TIA-Portal-version',
                              nargs   = "?",
                              const   = default_tia,
                              type    = str
                             )

        plc_args.add_argument(
                              '--plc-beckhoff',
                              dest    = "beckhoff",
                              help    = "use the default templates for Beckhoff PLCs and generate interface Beckhoff PLC comms. 'Beckhoff-version' is not used right now",
                              metavar = 'Beckhoff-version',
                              nargs   = "?",
                              const   = 'not-used',
                              type    = str
                             )

        plc_args.add_argument(
                              '--plc-opc',
                              dest    = "opc",
                              help    = "use the default templates for OPC-UA. No PLC code is generated!",
                              action  = "store_true",
                             )

        diag_args = plc_group.add_mutually_exclusive_group()
        diag_args.add_argument(
                               '--plc-no-diag',
                               dest     = "plc_no_diag",
                               help     = 'do not generate PLC diagnostics code (if used with --plc-x). This is the default',
                               action   = 'store_true',
                               default  = True,
                               required = False)

        diag_args.add_argument(
                               '--plc-diag',
                               dest     = "plc_no_diag",
                               help     = 'generate PLC diagnostics code (if used with --plc-x)',
                               action   = 'store_false',
                               required = False)

        diag_args.add_argument(
                               '--plc-only-diag',
                               dest     = "plc_only_diag",
                               help     = 'generate PLC diagnostics code only (if used with --plc-x)',
                               action   = 'store_true',
                               required = False)

        test_args = plc_group.add_mutually_exclusive_group()
        test_args.add_argument(
                               '--plc-no-test',
                               dest     = "plc_test",
                               help     = 'do not generate PLC comms testing code (if used with --plc-x). This is the default',
                               action   = 'store_false',
                               default  = False,
                               required = False)

        test_args.add_argument(
                               '--plc-test',
                               dest     = "plc_test",
                               help     = 'generate PLC comms testing code (if used with --plc-x)',
                               action   = 'store_true',
                               required = False)

        plc_group.add_argument(
                               '--plc-readonly',
                               dest     = "plc_readonly",
                               help     = 'do not generate EPICS --> PLC communication code',
                               action   = 'store_true',
                               default  = False)

        parser.add_argument(
                            '--list-templates',
                            dest    = "list_templates",
                            help    = "give a list of the possible templates that can be generated on-the-fly from an Interface Definition",
                            action  = "store_true"
                           )

        parser.add_argument(
                            '--enable-experimental',
                            dest    = 'experimental',
                            help    = 'enable experimental features',
                            action  = "store_true"
                           )

        return parser


    def add_eee_arg(parser):
        parser.add_argument(
                            '--eee',
                            dest    = "eee",
                            help    = "create a minimal EEE module with EPICS-DB and startup snippet",
                            metavar = "modulename",
                            nargs   = "?",
                            type    = str,
                            const   = ""
                           )

        parser.add_argument(
                            '--e3',
                            dest    = "e3",
                            help    = "create a minimal E3 module with EPICS-DB and startup snippet",
                            metavar = "modulename",
                            nargs   = "?",
                            type    = str,
                            const   = ""
                           )

        parser.add_argument(
                            '--ioc',
                            dest     = "ioc",
                            help     = "Generate IOC and if git repository is defined tag it with the given version",
                            metavar  = 'version',
                            type     = str,
                            const    = "",
                            nargs    = '?')

        return parser


    if git.check_for_updates(helpers.create_data_dir(__product__), "PLC Factory"):
        return

    parser = argparse.ArgumentParser(add_help = False)

    add_common_parser_args(parser)

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        const    = None
                       )

    # First pass
    #  get the device
    args   = parser.parse_known_args(argv)[0]
    device = args.device
    plc    = False

    if args.list_templates:
        print(tf.available_printers())
        return

    if args.siemens is not None:
        from interface_factory import IFA
        tia_version  = args.siemens.lower()
        try:
            tia_version  = IFA.consolidate_tia_version(tia_version)
        except IFA.FatalException as e:
            raise PLCFArgumentError(e.message)
        siemens      = True
    else:
        tia_version = None
        siemens     = False

    beckhoff = args.beckhoff

    opc = args.opc


    # Second pass
    #  get EEE and E3
    add_eee_arg(parser)

    args = parser.parse_known_args(argv)[0]

    eee_modulename = None
    e3_modulename  = None
    if args.eee is not None:
        if args.eee != "":
            eee_modulename = args.eee.lower()
            if eee_modulename.startswith('m-epics-'):
                eee_modulename = eee_modulename[len('m-epics-'):]
        glob.eee_modulename = eee_modulename
        glob.eee_snippet    = eee_modulename
        eee = True
    else:
        eee = False

    if args.ioc is not None:
        global generate_ioc
        generate_ioc = True

    if args.e3 is not None:
        global e3
        e3 = E3(args.e3)

    # Third pass
    #  get all options
    parser         = PLCFArgumentParser()

    add_common_parser_args(parser)
    add_eee_arg(parser)

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        required = True
                       )

    parser.add_argument(
                        '--zip',
                        dest    = "zipit",
                        help    = 'create a zipfile containing the generated files',
                        metavar = "zipfile-name",
                        nargs   = "?",
                        type    = str,
                        const   = device
                       )

    parser.add_argument(
                        '--root',
                        dest    = "root",
                        help    = 'use this prefix instead of the device / installation slot',
                        metavar = "root-installation-slot",
                        type    = str
                       )

    CC.addArgs(parser)

    parser.add_argument(
                        '--verify',
                        dest     = "verify",
                        help     = 'verify that the contents of the generated files did not change from the last run',
                        metavar  = "strictness",
                        type     = int,
                        const    = 1,
                        nargs    = '?')

    parser.add_argument(
                        '--verify-ignore',
                        dest     = "verify_ignore",
                        help     = 'ignore the specified templates while verifying. Comma separated list',
                        type     = str,
                        default  = "")

    parser.add_argument(
                        '--tag',
                        help     = 'tag to use if more than one matching artifact is found',
                        type     = not_empty_string)

    parser.add_argument(
                        '--epi-version',
                        dest     = "epi_version",
                        help     = "'EPI VERSION' to use. Overrides any 'EPI VERSION' property set in CCDB",
                        type     = not_empty_string)

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '+',
                        type     = str,
                        default  = [],
                        required = not (siemens or eee or e3 or beckhoff or opc))

    global OUTPUT_DIR
    parser.add_argument(
                        '--output',
                        dest     = 'output_dir',
                        help     = 'the output directory. Default: {}/'.format(OUTPUT_DIR),
                        type     = str,
                        default  = OUTPUT_DIR)

    # retrieve parameters
    args       = parser.parse_args(argv)

    start_time     = time.time()

    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    if args.root is not None:
        glob.root_installation_slot = args.root
    else:
        glob.root_installation_slot = device

    ifdef_params["ROOT_INSTALLATION_SLOT"] = glob.root_installation_slot

    glob.commit_id = commit_id if not args.verify else "N/A"
    glob.branch    = branch if not args.verify else "N/A"
    glob.cmdline   = " ".join(sys.argv) if not args.verify else "N/A"
    glob.origin    = git.get_origin()

    global device_tag
    device_tag = args.tag
    global epi_version
    epi_version = args.epi_version

    default_printers = set(["DEVICE-LIST", "README"])

    if siemens:
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "IFA", "ARCHIVE", "BEAST", "BEAST-TEMPLATE" ] )
        plc = True

    ifdef_params["PLC_READONLY"] = args.plc_readonly
    ifdef_params["EXPERIMENTAL"] = args.experimental

    if beckhoff:
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "IFA", "ARCHIVE", "BEAST", "BEAST-TEMPLATE" ] )
        ifdef_params["PLC_TYPE"] = "BECKHOFF"
        plc = True

    if opc:
        # EPICS-DB will be deleted later, but we add it here so that it is enough to check for EPICS-DB
        default_printers.update( [ "EPICS-DB", "EPICS-OPC-DB", "BEAST", "BEAST-TEMPLATE" ] )
        ifdef_params["PLC_TYPE"] = "OPC"
        plc = True

    if not plc and (eee or e3):
        raise PLCFArgumentError("Generating EEE or E3 modules is only supported with PLC integration")

    if eee:
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "AUTOSAVE-ST-CMD", "AUTOSAVE", "BEAST", "BEAST-TEMPLATE" ] )

    if e3 or generate_ioc:
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "AUTOSAVE-IOCSH", "BEAST", "BEAST-TEMPLATE", ] )

    if default_printers:
        if not default_printers <= set(tf.available_printers()):
            raise PLCFArgumentError("Your PLCFactory does not support generating the following necessary templates: {}".format(list(default_printers - set(tf.available_printers()))))

        templateIDs = default_printers | set(args.template)
    else:
        templateIDs = set(args.template)

    if opc and "OPC-MAP.XLS" in tf.available_printers():
        templateIDs.update( [ "OPC-MAP.XLS" ] )

    if (args.plc_only_diag or args.plc_no_diag is False) and not siemens:
        raise PLCFArgumentError('--plc-only-diag requires --plc-interface/--plc-siemens')

    if (args.plc_only_diag or args.plc_no_diag is False) and beckhoff:
        raise PLCFArgumentError('PLCFactory cannot (yet?) generate diagnostics code for Beckhoff PLCs')

    # FIXME: these tests should be put somewhere in the template_factory/printers section
    if eee and "EPICS-TEST-DB" in templateIDs:
        templateIDs.add("AUTOSAVE-TEST")
        templateIDs.add("AUTOSAVE-ST-TEST-CMD")

    if (e3 or generate_ioc) and "EPICS-TEST-DB" in templateIDs:
        templateIDs.add("AUTOSAVE-TEST-IOCSH")

    if "ST-CMD" in templateIDs and "AUTOSAVE-ST-CMD" in templateIDs:
        templateIDs.remove("ST-CMD")

    if "ST-TEST-CMD" in templateIDs and "AUTOSAVE-ST-TEST-CMD" in templateIDs:
        templateIDs.remove("ST-TEST-CMD")

    if "IOCSH" in templateIDs and "AUTOSAVE-IOCSH" in templateIDs:
        templateIDs.remove("IOCSH")

    if "TEST-IOCSH" in templateIDs and "AUTOSAVE-TEST-IOCSH" in templateIDs:
        templateIDs.remove("TEST-IOCSH")

    if "EPICS-DB" in templateIDs and opc:
        templateIDs.add("EPICS-OPC-DB")
        templateIDs.remove("EPICS-DB")

    os.system('clear')

    banner()

    if args.ccdb_test:
        from ccdb import CCDB_TEST
        glob.ccdb = CCDB_TEST(clear_templates = args.clear_ccdb_cache)
    elif args.ccdb_devel:
        from ccdb import CCDB_DEVEL
        glob.ccdb = CCDB_DEVEL(clear_templates = args.clear_ccdb_cache)
    else:
        glob.ccdb = CC.open(args.ccdb, clear_templates = args.clear_ccdb_cache)

    if args.output_dir[0] == '+':
        OUTPUT_DIR = os.path.join(OUTPUT_DIR, args.output_dir[1:])
    elif args.output_dir[-1] == '+':
        OUTPUT_DIR = os.path.join(args.output_dir[:-1], helpers.sanitizeFilename(device.lower()))
    elif args.output_dir == OUTPUT_DIR:
        OUTPUT_DIR = os.path.join(args.output_dir, helpers.sanitizeFilename(device.lower()))
    else:
        OUTPUT_DIR = args.output_dir

    if device_tag:
        OUTPUT_DIR = os.path.join(OUTPUT_DIR, helpers.sanitizeFilename(CC.TAG_SEPARATOR.join([ "", "tag", device_tag ])))
    helpers.makedirs(OUTPUT_DIR)

    read_data_files()
    if args.verify:
        obtain_previous_files()
        # Remove commit-id when verifying
        ifdef_params.pop("COMMIT_ID", commit_id)

    root_device = processDevice(device, list(templateIDs))

    if siemens or args.plc_only_diag or beckhoff:
        from interface_factory import IFA

        output_files.update(IFA.produce(OUTPUT_DIR, output_files["IFA"], TIAVersion = tia_version, nodiag = args.plc_no_diag, onlydiag = args.plc_only_diag, commstest = args.plc_test, verify = args.verify, readonly = args.plc_readonly))

    # create a factory of CCDB
    try:
        output_files["CCDB-FACTORY"] = root_device.toFactory(device, OUTPUT_DIR, git_tag = epi_version, script = "-".join([ device, glob.timestamp ]))
    except CC.Exception:
        pass

    # Verify created files: they should be the same as the ones from the last run
    if args.verify:
        verify_output(args.verify, args.verify_ignore)

    create_previous_files()
    write_data_files()

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.save("-".join([ device, glob.timestamp ]), OUTPUT_DIR)

    # record the arguments used to run this instance
    record_args(root_device)

    if plc:
        if eee:
            create_eee(glob.eee_modulename, glob.eee_snippet)
        if e3:
            e3.create()
        if ioc is not None:
            ioc.create(args.ioc)

    if args.zipit is not None:
        create_zipfile(args.zipit)

    has_warns = False
    for ifdef in ifdefs.itervalues():
        if ifdef is None:
            continue

        for warn in ifdef.warnings():
            if not has_warns:
                has_warns = True
                print("\nThe following warnings were detected:\n", file = sys.stderr)
            print(warn, file = sys.stderr)

    if not args.clear_ccdb_cache:
        print("\nTemplates were reused\n")

    try:
        if prev_hashes is not None and prev_hashes[root_device.name()][1] != hashes[root_device.name()][1]:
            print("""
+++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Be aware:                                         +
+	Our records show that the hash has changed. +
+++++++++++++++++++++++++++++++++++++++++++++++++++++
""")
    except KeyError:
        pass

    print("--- %.1f seconds ---" % (time.time() - start_time))

    if not taint_message():
        # As requested by Miklos :)
        print("---  ✨ 🍰 ✨ \n")
    else:
        print("--- No cake for you!\n")




if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFactoryException as e:
        if e.status:
            print(e, file = sys.stderr)
        exit(e.status)
