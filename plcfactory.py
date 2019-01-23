#!/usr/bin/python2

from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Entry point """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__credits__    = [ "Gregor Ulm"
                 , "David Brodrick"
                 , "Nick Levchenko"
                 , "Francois Bellorini"
                 , "Ricardo Fernandes"
                 ]
__license__    = "GPLv3"
__maintainer__ = "Gregor Ulm"
__email__      = "gregor.ulm@esss.se"
__status__     = "Production"
__env__        = "Python version 2.7"

# Python libraries
import argparse
import datetime
import os
import errno
import sys
import time
import hashlib
import zlib
from shutil import copy2, copyfileobj
from ast    import literal_eval as ast_literal_eval

# Template Factory
parent_dir = os.path.abspath(os.path.dirname(__file__))
tf_dir     = os.path.join(parent_dir, 'template_factory')
sys.path.append(tf_dir)
del tf_dir

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
import processTemplate as pt
from   ccdb import CCDB
import helpers
import plcf_git as git


# global variables
OUTPUT_DIR      = "output"
MODULES_DIR     = os.path.join(os.path.dirname(__file__), "module_templates")
TEMPLATE_TAG    = "TEMPLATE"
HEADER_TAG      = "HEADER"
FOOTER_TAG      = "FOOTER"
IFDEF_EXTENSION = ".def"
hashobj         = None
ifdefs          = dict()
ifdef_params    = dict(PLC_TYPE = "SIEMENS")
output_files    = dict()
previous_files  = None
device_tag      = None
hashes          = dict()
prev_hashes     = None
branch          = git.get_current_branch()
commit_id       = git.get_local_ref(branch)
if commit_id is not None:
    ifdef_params["COMMIT_ID"] = commit_id


class PLCFactoryException(Exception):
    status = 1



class ProcessTemplateException(PLCFactoryException):
    def __init__(self, device, template, exception, *args):
        super(ProcessTemplateException, self).__init__(*args)
        self.device    = device
        self.template  = template
        self.exception = exception


    def __str__(self):
        return """
The following exception occured during the processing of template '{template}' on device '{device}':
{exc}: {msg}""".format(template = self.template,
                       device   = self.device,
                       exc      = type(self.exception).__name__,
                       msg      = self.exception)



class Hasher(object):
    def __init__(self, hash_base = None):
        self._hashobj = hashlib.sha256(hash_base)


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



def initializeHash(hash_base = None):
    return Hasher(hash_base)


def openTemplate(device, tag, templateID):
    assert isinstance(tag,        str)
    assert isinstance(templateID, str)

    matches = filter(lambda f: matchingArtifact(f, (tag, TEMPLATE_TAG), templateID), device.artifacts())

    if not matches:
        return []

    if len(matches) > 1:
        raise RuntimeError("More than one possible matching artifacts found for {template}: {artifacts}".format(template  = "_".join([ tag, TEMPLATE_TAG, templateID ]),
                                                                                                                artifacts = matches))

    filename = matches[0].download()

    with open(filename) as f:
        lines = f.readlines()

    return lines


def downloadTemplate(device, templateID):
    assert isinstance(templateID, str)

    matches = filter(lambda f:matchingArtifact(f, TEMPLATE_TAG, templateID), device.artifacts())

    if not matches:
        return None

    if len(matches) > 1:
        raise RuntimeError("More than one possible matching artifacts found for {template}: {artifacts}".format(template  = "_".join([ TEMPLATE_TAG, templateID ]),
                                                                                                                artifacts = matches))

    return matches[0].download()


def matchingArtifact(artifact, tag, templateID):
    if not artifact.is_file():
        return False

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


def createFilename(header, device, templateID, **kwargs):
    assert isinstance(header,     list)
    assert isinstance(templateID, str )

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if len(header) == 0 or tagPos == -1:
        outputFile = device.name() + "_" + device.deviceType() + "_template-" + templateID \
                   + "_" + glob.timestamp + ".scl"

        return helpers.sanitizeFilename(outputFile)

    else:
        filename = header[tagPos]

        # remove tag and strip surrounding whitespace
        filename = filename[len(tag):].strip()
        filename = plcf.keywordsHeader(filename, device, templateID, **kwargs)

        return helpers.sanitizeFilename(filename)


def findTag(lines, tag):
    tagPos = -1

    if not lines:
        return tagPos

    assert isinstance(lines, list)
    assert isinstance(tag,   str )

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
            break

    if pos == -1:
        return header

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
    deviceType = device.deviceType()

    if deviceType in ifdefs:
        return ifdefs[deviceType]

    filename = device.downloadArtifact(IFDEF_EXTENSION, device_tag, filetype = "Interface Definition")
    if filename is None:
        # No 'file' artifact found, let's see if there is a URL
        filename = device.downloadExternalLink("EPI", IFDEF_EXTENSION, device_tag, "Interface Definition")
        if filename is None:
            return None

    with open(filename) as f:
        ifdef = tf.processLines(f, FILENAME = filename)

    if ifdef is not None:
        ifdefs[deviceType] = ifdef

    return ifdef


def getHeaderFooter(device, templateID):
    assert isinstance(templateID, str)

    templatePrinter = tf.get_printer(templateID)
    if templatePrinter is not None:
        print("Using built-in template header/footer")
        header = []
        templatePrinter.header(header, **ifdef_params)
        footer = []
        templatePrinter.footer(footer)
    else:
        header = openTemplate(device, HEADER_TAG, templateID)
        footer = openTemplate(device, FOOTER_TAG, templateID)

    if not header:
        print("No header found.\n")
    else:
        print("Header read.\n")

    if not footer:
        print("No footer found.\n")
    else:
        print("Footer read.\n")

    return (header, footer, templatePrinter)


def processTemplateID(templateID, devices):
    assert isinstance(templateID,      str)
    assert isinstance(devices,         list)

    start_time = time.time()

    rootDevice = devices[0]

    if device_tag:
        tagged_templateID = "_".join([ device_tag, templateID ])
    else:
        tagged_templateID = templateID

    print("#" * 60)
    print("Template ID " + tagged_templateID)
    print("Device at root: " + str(rootDevice) + "\n")

    # collect lines to be written at the end
    output = []

    # process header/footer
    (header, footer, templatePrinter) = getHeaderFooter(rootDevice, templateID)
    # has to acquire filename _before_ processing the header
    # there are some special tags that are only valid in the header
    outputFile = os.path.join(OUTPUT_DIR, createFilename(header, rootDevice, templateID))

    if header:
        header = pt.process(rootDevice, header)

    if footer:
        footer = pt.process(rootDevice, footer)

    print("Processing entire tree of controls-relationships:\n")

    can_combine   = tf.is_combinable(templateID)
    def_seen      = None
    template_seen = None

    # for each device, find corresponding template and process it
    output     = []
    for device in devices:
        deviceType = device.deviceType()

        print(device.name())
        print("Device type: " + deviceType)

        hashobj.update(device.name().encode())

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
                templatePrinter.body(ifdef, template)

        # Try to download template from artifact
        if template is None:
            template = downloadTemplate(device, "_" + tagged_templateID if device_tag else tagged_templateID)
            if template is not None:
                template_seen = True

        if def_seen and template_seen and not can_combine:
            raise RuntimeError("Cannot combine Interface Definitions and ordinary templates with {}".format(templateID))

        # Try to check if we have a default template printer implementation
        if template is None and templatePrinter is not None and not templatePrinter.needs_ifdef():
            print("Using default built-in template...")
            template = []
            templatePrinter.body(None, template)

        if template is not None:
            # process template and add result to output
            try:
                output += pt.process(device, template)
            except (plcf.PLCFException, PLCFExtException) as e:
                raise ProcessTemplateException(device.name(), templateID, e)

            print("Template processed.")

        else:
            print("No template found.")

        print("=" * 40)

    print("\n")

    if not def_seen:
        glob.ccdb.computeHash(hashobj)

    # process #HASH keyword in header and footer
    header      = processHash(header)
    footer      = processHash(footer)

    eol         = getEOL(header)

    output      = header + output + footer

    if not output:
        print("There were no templates for ID = {}.\n".format(tagged_templateID))
        return

    lines  = output
    output = []

    # Process counters; initialize
    numOfCounters = 9
    counters      = dict()

    for n in range(numOfCounters):
        counters["Counter" + str(n + 1)] = 0


    for line in lines:

        if "[PLCF#" in line and "#COUNTER" not in line:
            line = plcf.evalCounter(line, counters)

        elif "[PLCF#" in line and '#COUNTER' in line:
            (counters, line) = plcf.evalCounterIncrease(line, counters)

        assert isinstance(line, str)
        # PLCF should now all be be processed
        assert "[PLCF#" not in line, "Leftover PLCF# expression in line: {line}".format(line = line)
        output.append(line)


    #write file
    with open(outputFile,'w') as f:
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


def processDevice(deviceName, templateIDs):
    assert isinstance(deviceName,  str)
    assert isinstance(templateIDs, list)

    try:
        print("Obtaining controls tree...", end = '', flush = True)
    except TypeError:
        print("Obtaining controls tree...", end = '')
        sys.stdout.flush()

    device = glob.ccdb.device(deviceName)

    if glob.modulename is None:
        dev_props = device.properties()
        modulename = dev_props.get("EPICSModule", [])
        if len(modulename) == 1:
            glob.modulename = modulename[0]
        else:
            glob.modulename = helpers.sanitizeFilename(deviceName.lower())

        snippet = dev_props.get("EPICSSnippet", [])
        if len(snippet) == 1:
            glob.snippet = snippet[0]
        else:
            glob.snippet = glob.modulename

    hash_base = """EPICSToPLCDataBlockStartOffset: [PLCF#EPICSToPLCDataBlockStartOffset]
PLCToEPICSDataBlockStartOffset: [PLCF#PLCToEPICSDataBlockStartOffset]
PLC-EPICS-COMMS:Endianness: [PLCF#PLC-EPICS-COMMS:Endianness]"""
    hash_base = "\n".join(pt.process(device, hash_base.splitlines()))

    # create a stable list of controlled devices
    devices = device.buildControlsList(include_self = True, verbose = True)

    for templateID in templateIDs:
        global hashobj
        hashobj = initializeHash(hash_base)

        processTemplateID(templateID, devices)

    global hashes
    cur_hash = (hashobj.getHash(), hashobj.getCRC32())
    hashes[device.name()] = cur_hash

    try:
        prev_hash = prev_hashes[device.name()]
        # Check if CRC32 is the same but the actual hash is different
        if prev_hash[0] is not None and prev_hash[0] != cur_hash[0] and prev_hash[1] == cur_hash[1]:
            raise RuntimeError("CRC32 collision detected. Please file a bug report")
    except (KeyError, TypeError):
        pass

    return device


def create_zipfile(zipit):
    import zipfile

    if not zipit.endswith(".zip"):
        zipit += ".zip"

    zipit = helpers.sanitizeFilename(zipit)

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
                with open(dstname, 'w') as f:
                    for line in pt.process(None, srcname):
                        print(line, end = '', file = f)
            else:
                copy2(srcname, dstname)

    return copied


def create_eee(modulename, snippet):
    eee_files = []
    out_mdir  = os.path.join(OUTPUT_DIR, "modules", "-".join([ "m-epics", modulename ]))
    helpers.makedirs(out_mdir)

    def makedir(d):
        od = os.path.join(out_mdir, d)
        helpers.makedirs(od)
        return od

    from shutil import copy2, copyfileobj
    def m_cp(f, d, newname):
        of = os.path.join(makedir(d), newname)
        copy2(f, of)
        eee_files.append(of)

    eee_files.extend(m_copytree(os.path.join(MODULES_DIR, "eee"), out_mdir))

    #
    # Copy files
    #
    with open(os.path.join(makedir("db"), modulename + ".db"), "w") as dbfile:
        for parts in [ output_files.get('EPICS-DB', output_files.get('EPICS-OPC-DB')), output_files['UPLOAD-PARAMS'] ]:
            with open(parts) as partfile:
                copyfileobj(partfile, dbfile)
        output_files['EEE-DB'] = dbfile.name

    try:
        m_cp(output_files['EPICS-TEST-DB'],           "db",      modulename + "-test.db")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-ST-CMD'],         "startup", snippet + ".cmd")
    except KeyError:
        m_cp(output_files['ST-CMD'],                  "startup", snippet + ".cmd")

    test_cmd = True
    try:
        m_cp(output_files['AUTOSAVE-ST-TEST-CMD'],    "startup", snippet + "-test.cmd")
    except KeyError:
        try:
            m_cp(output_files['ST-TEST-CMD'],         "startup", snippet + "-test.cmd")
        except KeyError:
            test_cmd = False

    req_files    = []
    try:
        m_cp(output_files['AUTOSAVE'],                "misc",    modulename + ".req")
        req_files.append(modulename + ".req")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-TEST'],           "misc",    modulename + "-test.req")
        req_files.append(modulename + "-test.req")
    except KeyError:
        pass

    m_cp(output_files["CREATOR"],                     "misc",    "creator")

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

    output_files['EEE'] = eee_files

    #
    # Create script to run module with 'safe' defaults
    #
    with open(os.path.join(OUTPUT_DIR, "run_module"), "w") as run:
        if 'OPC' in ifdef_params['PLC_TYPE']:
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}.cmd, "IPADDR=127.0.0.1, PORT=4840, PUBLISHING_INTERVAL=200")'""".format(modulename = modulename,
                                                                                                                                                      snippet    = snippet), file = run)
        else:
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}.cmd, "IPADDR=127.0.0.1, RECVTIMEOUT=3000")'""".format(modulename = modulename,
                                                                                                                                    snippet    = snippet), file = run)

    if test_cmd:
        #
        # Create script to run test version of module
        #
        with open(os.path.join(OUTPUT_DIR, "run_test_module"), "w") as run:
            print("""iocsh -r {modulename},local -c 'requireSnippet({snippet}-test.cmd)'""".format(modulename = modulename,
                                                                                                   snippet    = snippet), file = run)

    print("EEE Module created:", out_mdir)
    return out_mdir


def create_data_dir():
    dname = os.path.join(os.path.expanduser("~"), ".local/share/ics_plc_factory")
    helpers.makedirs(dname)

    return dname


def read_data_files():
    global hashes
    global prev_hashes

    try:
        with open(os.path.join(create_data_dir(), "hashes")) as h:
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


def create_e3(modulename, snippet):
    e3_files = []
    out_mdir = os.path.join(OUTPUT_DIR, "modules", "-".join([ "e3", modulename ]))
    helpers.makedirs(out_mdir)

    def makedir(d):
        od = os.path.join(out_sdir, d)
        helpers.makedirs(od)
        return od

    def m_cp(f, d, newname):
        of = os.path.join(makedir(d), newname)
        copy2(f, of)
        e3_files.append(of)

    e3_files.extend(m_copytree(os.path.join(MODULES_DIR, "e3"), out_mdir))

    out_sdir = os.path.join(out_mdir, "-".join([ modulename, "loc" ]))
    helpers.makedirs(out_sdir)

    #
    # Copy files
    #
    with open(os.path.join(makedir("db"), modulename + ".db"), "w") as dbfile:
        for parts in [ output_files.get('EPICS-DB', output_files.get('EPICS-OPC-DB')), output_files['UPLOAD-PARAMS'] ]:
            with open(parts) as partfile:
                copyfileobj(partfile, dbfile)
        output_files['E3-DB'] = dbfile.name

    try:
        m_cp(output_files['EPICS-TEST-DB'],           "db",      modulename + "-test.db")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-IOCSH'],          "iocsh",   snippet + ".iocsh")
    except KeyError:
        m_cp(output_files['IOCSH'],                   "iocsh",   snippet + ".iocsh")

    test_cmd = True
    try:
        m_cp(output_files['AUTOSAVE-TEST-IOCSH'],     "iocsh",   snippet + "-test.iocsh")
    except KeyError:
        try:
            m_cp(output_files['TEST-IOCSH'],          "iocsh",   snippet + "-test.iocsh")
        except KeyError:
            test_cmd = False

    req_files    = []
    try:
        m_cp(output_files['AUTOSAVE'],                "misc",    modulename + ".req")
        req_files.append(modulename + ".req")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-TEST'],           "misc",    modulename + "-test.req")
        req_files.append(modulename + "-test.req")
    except KeyError:
        pass

    m_cp(output_files["CREATOR"],                     "misc",    "creator")

    #
    # Copy CCDB dump
    #
    if output_files['CCDB-DUMP'] is not None:
        miscdir = os.path.join(out_sdir, "misc")
        try:
            import zipfile
            with zipfile.ZipFile(output_files['CCDB-DUMP'], "r") as z:
                z.extractall(miscdir)
                e3_files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
                z.close()
        except:
            helpers.rmdirs(os.path.join(miscdir, "ccdb"))
            print("Cannot copy CCDB dump to E3 module")


    output_files['E3'] = e3_files

    print("E3 Module created:", out_mdir)
    return out_mdir


def write_data_files():
    try:
        with open(os.path.join(create_data_dir(), "hashes"), 'w') as h:
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


def verify_output(strictness):
    if strictness == 0 or (previous_files is None and strictness < 3):
        return

    ignored_templates = [ 'PREVIOUS_FILES', 'CREATOR', 'CCDB-DUMP' ]
    for template in ignored_templates:
        previous_files.pop(template, None)

    import filecmp
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

        #compare prev and output
        try:
            if filecmp.cmp(prev, output, shallow = 0):
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
    creator = os.path.join(OUTPUT_DIR, createFilename(["#FILENAME [PLCF#INSTALLATION_SLOT]-creator-[PLCF#TIMESTAMP]"], root_device, ""))
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



def check_for_updates():
    local_ref = git.get_local_ref()

    if local_ref is None:
        print("Could not check local version")
        return False

    check_time = time.time()

    try:
        with open(os.path.join(create_data_dir(), "updates")) as u:
            raw_updates = u.readline()
        updates = ast_literal_eval(raw_updates)
        if updates[0] + 600 > check_time:
            if local_ref != updates[1]:
                print("An update is available")
            return False
    except:
        pass

    print("Checking for updates...")
    remote_ref = git.get_remote_ref()
    if remote_ref is None:
        print("Could not check for updates")
        return False

    # Check if we have remote ref. True means we are most probably ahead of origin; ignore remote ref then
    if git.has_commit(remote_ref):
        remote_ref = local_ref

    updates = (check_time, remote_ref)
    try:
        with open(os.path.join(create_data_dir(), "updates"), "w") as u:
            print(updates, file = u)
    except:
        pass

    if remote_ref != local_ref:
        print("""
An update to PLC Factory is available.

Please run `git pull`
""")
        return True

    return False


class PLCFArgumentError(Exception):
    def __init__(self, status, message = None):
        self.status  = status
        self.message = message


class PLCFArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        argparse.ArgumentParser.__init__(self)


    def exit(self, status = 0, message = None):
        if message:
            self._print_message(message, sys.stderr)

        raise PLCFArgumentError(status)


def main(argv):
    def add_common_parser_args(parser):
        #
        # -d/--device cannot be added to the common args, because it is not a required option in the first pass but a required one in the second pass
        #
        plc_group = parser.add_argument_group("PLC related options")

        plc_args = plc_group.add_mutually_exclusive_group()

        plc_args.add_argument(
                              '--plc-interface',
                              dest    = "plc_interface",
                              help    = 'use the default templates for PLCs and generate interface PLC comms. The default TIA version is TIAv14',
                              metavar = 'TIA-Portal-version',
                              nargs   = "?",
                              const   = 'TIAv14',
                              type    = str
                             )

        plc_args.add_argument(
                              '--plc-direct',
                              dest    = "plc_direct",
                              help    = 'use the default templates for PLCs and generate direct PLC comms. The default TIA version is TIAv14',
                              metavar = 'TIA-Portal-version',
                              nargs   = "?",
                              const   = 'TIAv14',
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

        parser.add_argument(
                            '--list-templates',
                            dest    = "list_templates",
                            help    = "give a list of the possible templates that can be generated on-the-fly from an Interface Definition",
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

        return parser


    if check_for_updates():
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

    if args.list_templates:
        print(tf.available_printers())
        return

    def consolidate_tia_version(tia_version):
        if tia_version is not None and isinstance(tia_version, str):
            tia13 = set({"13", "v13", "tia13", "tiav13"})
            tia14 = set({"14", "v14", "tia14", "tiav14"})

            if tia_version in tia13:
                tia_version = 13
            elif tia_version in tia14:
                tia_version = 14
            else:
                raise PLCFArgumentError(1, "Invalid TIA version: " + tia_version)

        return tia_version

    if args.plc_direct is not None:
        tia_version        = args.plc_direct.lower()
        tia_map            = "TIA-MAP-DIRECT"
        args.plc_direct    = True
        args.plc_interface = False
    elif args.plc_interface is not None:
        tia_version        = args.plc_interface.lower()
        tia_map            = None
        args.plc_interface = True
        args.plc_direct    = False
    else:
        tia_version = None
        tia_map     = None

    beckhoff = args.beckhoff

    opc = args.opc

    tia_version = consolidate_tia_version(tia_version)

    # Second pass
    #  get EEE and E3
    add_eee_arg(parser)

    args = parser.parse_known_args(argv)[0]

    modulename = None
    if args.eee is not None:
        if args.eee != "":
            modulename = args.eee.lower()
            if modulename.startswith('m-epics-'):
                modulename = modulename[len('m-epics-'):]
        eee = True
    else:
        eee = False

    if args.e3 is not None:
        if args.e3 != "":
            e3 = args.e3.lower()
            if e3.startswith('e3-'):
                e3 = e3[len('e3-'):]
        e3 = True
    else:
        e3 = False

    if modulename:
        glob.modulename = modulename
        glob.snippet    = modulename

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

    ccdb_args = parser.add_argument_group("CCDB related options").add_mutually_exclusive_group()
    ccdb_args.add_argument(
                           '--ccdb-test',
                           '--test',
                           dest     = "ccdb_test",
                           help     = 'select CCDB test database',
                           action   = 'store_true',
                           required = False)

    ccdb_args.add_argument(
                           '--ccdb-devel',
                           dest     = "ccdb_devel",
                           help     = argparse.SUPPRESS, #selects CCDB development database
                           action   = 'store_true',
                           required = False)

    # this argument is just for show as the corresponding value is
    # set to True by default                        
    ccdb_args.add_argument(
                           '--ccdb-production',
                           '--production',
                           dest     = "ccdb_production",
                           help     = 'select production CCDB database',
                           action   = 'store_true',
                           required = False)

    ccdb_args.add_argument(
                           '--ccdb',
                           dest     = "ccdb",
                           help     = 'use a CCDB dump as backend',
                           metavar  = 'directory-to-CCDB-dump / name-of-.ccdb.zip',
                           type     = str,
                           required = False)

    parser.add_argument(
                        '--cached',
                        dest     = "clear_templates",
                        help     = 'do not clear "templates" folder; use the templates downloaded by a previous run',
                        # be aware of the inverse logic between the meaning of the option and the meaning of the variable
                        default  = True,
                        action   = 'store_false')

    parser.add_argument(
                        '--verify',
                        dest     = "verify",
                        help     = 'verify that the contents of the generated files did not change from the last run',
                        metavar  = "strictness",
                        type     = int,
                        const    = 1,
                        nargs    = '?')

    parser.add_argument(
                        '--tag',
                        help     = 'tag to use if more than one matching artifact is found',
                        type     = str)

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '+',
                        type     = str,
                        default  = [],
                        required = not (tia_version or eee or e3 or beckhoff or opc))

    # retrieve parameters
    args       = parser.parse_args(argv)

    start_time     = time.time()

    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    if args.root is not None:
        glob.root_installation_slot = args.root
    else:
        glob.root_installation_slot = device

    global device_tag
    device_tag = args.tag

    default_printers = set(["DEVICE-LIST"])

    if args.plc_interface:
        default_printers.update( [ "EPICS-DB", "IFA" ] )

    if args.plc_direct:
        tf.optimize_s7db(True)
        default_printers.update( [ "EPICS-DB", "IFA", tia_map ] )

    if beckhoff:
        default_printers.update( [ "EPICS-DB", "IFA" ] )
        ifdef_params["PLC_TYPE"] = "BECKHOFF"

    if opc:
        # EPICS-DB will be deleted later, but we add it here so that it is enough to check for EPICS-DB
        default_printers.update( [ "EPICS-DB", "EPICS-OPC-DB" ] )
        ifdef_params["PLC_TYPE"] = "OPC"

    if eee:
        default_printers.update( [ "EPICS-DB", "AUTOSAVE-ST-CMD", "AUTOSAVE" ] )

    if e3:
        default_printers.update( [ "EPICS-DB", "IOCSH", ] )

    if default_printers:
        if not default_printers <= set(tf.available_printers()):
            print("Your PLCFactory does not support generating the following necessary templates:", list(default_printers - set(tf.available_printers())))
            exit(1)

        templateIDs = default_printers | set(args.template)
    else:
        templateIDs = set(args.template)

    # Make sure that OPTIMIZE_S7DB is turned on if TIA-MAP-DIRECT is requested
    if "TIA-MAP-DIRECT" in templateIDs:
        tia_map = "TIA-MAP-DIRECT"
        tf.optimize_s7db(True)
        templateIDs.add("IFA")
        if args.plc_no_diag == False and not args.plc_direct:
            args.plc_only_diag =  True
            tia_version        =  14

    if (args.plc_only_diag or args.plc_no_diag == False) and tia_version is None:
        raise PLCFArgumentError('--plc-only-diag requires --plc-direct or --plc-interface')

    if (args.plc_only_diag or args.plc_no_diag == False) and beckhoff:
        raise PLCFArgumentError('PLCFactory cannot (yet?) generate diagnostics code for Beckhoff PLCs')

    if beckhoff and ( "TIA-MAP-DIRECT" in templateIDs or "TIA-MAP-INTERFACE" in templateIDs ):
        raise PLCFArgumentError("Cannot use --plc-beckhoff with TIA-MAPs")

    if "EPICS-DB" in templateIDs:
        templateIDs.add("UPLOAD-PARAMS")

    if eee and "EPICS-TEST-DB" in templateIDs:
        templateIDs.add("AUTOSAVE-TEST")
        templateIDs.add("AUTOSAVE-ST-TEST-CMD")

    if e3 and "EPICS-TEST-DB" in templateIDs:
        templateIDs.add("TEST-IOCSH")

    if "ST-CMD" in templateIDs and "AUTOSAVE-ST-CMD" in templateIDs:
        templateIDs.remove("ST-CMD")

    if "ST-TEST-CMD" in templateIDs and "AUTOSAVE-ST-TEST-CMD" in templateIDs:
        templateIDs.remove("ST-TEST-CMD")

    if "EPICS-DB" in templateIDs and opc:
        templateIDs.add("EPICS-OPC-DB")
        templateIDs.remove("EPICS-DB")

    os.system('clear')

    banner()

    if args.ccdb:
        from cc import CC
        glob.ccdb = CC.load(args.ccdb)
    elif args.ccdb_test:
        from ccdb import CCDB_TEST
        glob.ccdb = CCDB_TEST(clear_templates = args.clear_templates)
    elif args.ccdb_devel:
        from ccdb import CCDB_DEVEL
        glob.ccdb = CCDB_DEVEL(clear_templates = args.clear_templates)
    else:
        glob.ccdb = CCDB(clear_templates = args.clear_templates)

    global OUTPUT_DIR
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, helpers.sanitizeFilename(device.lower()))
    if device_tag:
        OUTPUT_DIR = os.path.join(OUTPUT_DIR, helpers.sanitizeFilename(CCDB.TAG_SEPARATOR.join([ "", "tag", device_tag ])))
    helpers.makedirs(OUTPUT_DIR)

    read_data_files()
    if args.verify:
        obtain_previous_files()
        # Remove commit-id when verifying
        ifdef_params.pop("COMMIT_ID", commit_id)

    root_device = processDevice(device, list(templateIDs))

    # Verify created files: they should be the same as the ones from the last run
    if args.verify:
        verify_output(args.verify)

    create_previous_files()
    write_data_files()

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.dump("-".join([ device, glob.timestamp ]), OUTPUT_DIR)

    # record the arguments used to run this instance
    record_args(root_device)

    if tia_version or args.plc_only_diag or beckhoff:
        from interface_factory import produce as ifa_produce

        output_files.update(ifa_produce(OUTPUT_DIR, output_files["IFA"], SclPath = output_files.get(tia_map, ""), TIAVersion = tia_version, nodiag = args.plc_no_diag, onlydiag = args.plc_only_diag, direct = args.plc_direct))

    if eee:
        create_eee(glob.modulename, glob.snippet)
    if e3:
        create_e3(glob.modulename, glob.snippet)

    if args.zipit is not None:
        create_zipfile(args.zipit)

    has_warns = False
    for ifdef in ifdefs.itervalues():
        for warn in ifdef.warnings():
            if not has_warns:
                has_warns = True
                print("\nThe following warnings were detected:\n", file = sys.stderr)
            print(warn, file = sys.stderr)

    if not args.clear_templates:
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

    print("--- %.1f seconds ---\n" % (time.time() - start_time))




if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFArgumentError as e:
        print(e.message, file = sys.stderr)
        exit(e.status)
    except PLCFactoryException as e:
        print(e)
        exit(e.status)
