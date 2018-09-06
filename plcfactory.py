#!/usr/bin/python2

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

# Template Factory
parent_dir = os.path.abspath(os.path.dirname(__file__))
tf_dir     = os.path.join(parent_dir, 'template_factory')
sys.path.append(tf_dir)
del tf_dir

try:
    import tf
except AttributeError, e:
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
import processTemplate as pt
from   ccdb import CCDB
from   future_print import future_print
import helpers

# global variables
OUTPUT_DIR   = "output"
TEMPLATE_TAG = "TEMPLATE"
HEADER_TAG   = "HEADER"
FOOTER_TAG   = "FOOTER"
IFDEF_TAG    = ".def"
hashobj      = hashlib.sha256()
ifdefs       = dict()
output_files = dict()
plc_type     = "SIEMENS"


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

        match  = "{}.txt".format("_".join([tag[0], tag[1], templateID]))
    else:
        assert isinstance(tag, str)

        # do not match HEADERs and FOOTERs if not in HEADER/FOOTER mode
        if HEADER_TAG in filename or FOOTER_TAG in filename:
            return False
        match  = "{}.txt".format("_".join([tag, templateID]))

    return filename.endswith(match)


def createFilename(header, device, templateID):
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
        filename = plcf.keywordsHeader(filename, device, templateID)

        return helpers.sanitizeFilename(filename)


def findTag(lines, tag):
    tagPos = -1

    if lines is None:
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

    hashSum     = glob.ccdb.getHash(hashobj)
    line        = header[pos]
    tagPos      = line.find(tag)
    line        = line[:tagPos] + hashSum + line[tagPos + len(tag):]
    header[pos] = line

    return header


def getEOL(header):
    assert isinstance(header, list)

    tag    = "#EOL"
    tagPos = findTag(header, tag)

    if len(header) == 0 or tagPos == -1:
        return "\n"

    # this really is a quick and dirty hack
    # should be replaced by something like
    # #EOL CR LF
    return header[tagPos][len(tag):].strip().replace('\\n', '\n').replace('\\r', '\r').translate(None, '"\'')


def replaceTag(line, tag, insert):
    assert isinstance(line,   str)
    assert isinstance(tag,    str)
    assert isinstance(insert, str)

    start = line.find(tag)
    assert start != -1

    end   = start + len(tag)

    return line[:start] + insert + line[end:]


def getIfDefFromURL(device):
    artifacts = filter(lambda u: u.is_uri() and u.name() == "EPI", device.artifacts())
    if not artifacts:
        return None

    if len(artifacts) > 1:
        raise RuntimeError("More than one Interface Definition URLs were found for {device}: {urls}".format(device = device.name(), urls = map(lambda u: u.uri(), artifacts)))

    filename = helpers.sanitizeFilename(device.deviceType().upper() + ".def")
    url = "/".join([ "raw/master", filename ])

    print "Downloading Interface Definition file {filename} from {url}".format(filename = filename,
                                                                               url      = artifacts[0].uri())

    return artifacts[0].download(extra_url = url)


#
# Returns an interface definition object
#
def getIfDef(device):
    deviceType = device.deviceType()

    if deviceType in ifdefs:
        return ifdefs[deviceType]

    defs = filter(lambda a: a.is_file() and a.filename().endswith(IFDEF_TAG), device.artifacts())

    if len(defs) > 1:
        raise RuntimeError("More than one Interface Definiton files were found for {device}: {defs}".format(device = device.name(), defs = defs))

    if defs:
        filename = defs[0].download()
    else:
        # No 'file' artifact found, let's see if there is a URL
        filename = getIfDefFromURL(device)
        if filename is None:
            return None

    with open(filename) as f:
        ifdef = tf.processLines(f, HASH = hashobj, FILENAME = filename)

    if ifdef is not None:
        ifdefs[deviceType] = ifdef

    return ifdef


def buildControlsList(device):
    device.putInControlledTree()

    # find devices this device _directly_ controls
    pool = device.controls()

    # find all devices that are directly or indirectly controlled by 'device'
    controlled_devices = set(pool)
    while pool:
        dev = pool.pop()

        cdevs = dev.controls()
        for cdev in cdevs:
            if cdev not in controlled_devices:
                controlled_devices.add(cdev)
                pool.append(cdev)

    # group them by device type
    pool = list(controlled_devices)
    controlled_devices = dict()
    for dev in pool:
        device_type = dev.deviceType()
        try:
            controlled_devices[device_type].append(dev)
        except KeyError:
            controlled_devices[device_type] = [ dev ]

    print "\r" + "#" * 60
    print "Device at root: " + device.name() + "\n"
    print device.name() + " controls: "

    # sort items into a list
    def sortkey(device):
        return device.name()
    pool = list()
    for device_type in sorted(controlled_devices):
        print "\t- " + device_type

        for dev in sorted(controlled_devices[device_type], key=sortkey):
            pool.append(dev)
            dev.putInControlledTree()
            print "\t\t-- " + dev.name()

    print "\n"

    return pool


def getHeaderFooter(device, templateID):
    assert isinstance(templateID, str)

    templatePrinter = tf.get_printer(templateID)
    if templatePrinter is not None:
        print "Using built-in template header/footer"
        header = []
        templatePrinter.header(header, PLC_TYPE = plc_type)
        footer = []
        templatePrinter.footer(footer)
    else:
        header = openTemplate(device, HEADER_TAG, templateID)
        footer = openTemplate(device, FOOTER_TAG, templateID)

    if not header:
        print "No header found.\n"
    else:
        print "Header read.\n"

    if not footer:
        print "No footer found.\n"
    else:
        print "Footer read.\n"

    return (header, footer, templatePrinter)


def processTemplateID(templateID, devices):
    assert isinstance(templateID,      str)
    assert isinstance(devices,         list)

    start_time = time.time()

    rootDevice = devices[0]

    print "#" * 60
    print "Template ID " + templateID
    print "Device at root: " + str(rootDevice) + "\n"

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

    print "Processing entire tree of controls-relationships:\n"

    # for each device, find corresponding template and process it
    output     = []
    for device in devices:
        deviceType = device.deviceType()

        print device.name()
        print "Device type: " + deviceType

        hashobj.update(device.name())

        # get template
        template = None

        # Try to process Interface Definition first
        if templatePrinter is not None:
            ifdef = getIfDef(device)
            if ifdef is not None:
                print "Generating template from Definition File..."
                template = []
                templatePrinter.body(ifdef, template)

        # Try to download template from artifact
        if template is None:
            template = downloadTemplate(device, templateID)

        # Try to check if we have a default template printer implementation
        if template is None and templatePrinter is not None:
            print "Using default built-in template..."
            template = []
            templatePrinter.body(None, template)

        if template is not None:
            # process template and add result to output
            output += pt.process(device, template)
            print "Template processed."

        else:
            print "No template found."

        print "=" * 40

    print "\n"

    # process #HASH keyword in header and footer
    header      = processHash(header)
    footer      = processHash(footer)

    eol         = getEOL(header)

    output      = header + output + footer

    if not output:
        print "There were no templates for ID = " + templateID + ".\n"
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
                future_print(line, end = eol, file = f)

    output_files[templateID] = outputFile

    print "Output file written: " + outputFile + "\n",
    print "Hash sum: " + glob.ccdb.getHash(hashobj)
    print("--- %s %.1f seconds ---\n" % (templateID, time.time() - start_time))


def processDevice(deviceName, templateIDs):
    assert isinstance(deviceName,  str)
    assert isinstance(templateIDs, list)

    print "Obtaining controls tree..."

    device = glob.ccdb.device(deviceName)

    # create a stable list of controlled devices
    devices = [ device ]
    devices.extend(buildControlsList(device))

    map(lambda x: processTemplateID(x, devices), templateIDs)


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

    print "Zipfile created: " + zipit
    return zipit


def create_eem(basename):
    eem_files = []
    out_mdir  = os.path.join(OUTPUT_DIR, "modules", "-".join(["m-epics", basename]))
    helpers.makedirs(out_mdir)

    def makedir(d):
        od = os.path.join(out_mdir, d)
        helpers.makedirs(od)
        return od

    from shutil import copy2, copyfileobj
    def m_cp(f, d, newname):
        of = os.path.join(makedir(d), newname)
        copy2(f, of)
        eem_files.append(of)

    #
    # Copy files
    #
    with open(os.path.join(makedir("db"), basename + ".db"), "w") as dbfile:
        for parts in [ output_files['EPICS-DB'], output_files['UPLOAD-PARAMS'] ]:
            with open(parts) as partfile:
                copyfileobj(partfile, dbfile)
        output_files['EEE-DB'] = dbfile.name

#    m_cp(output_files['EPICS-DB'],       "db",      basename + ".db")

    try:
        m_cp(output_files['EPICS-TEST-DB'],  "db",      basename + "-test.db")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-ST-CMD'],         "startup", basename + ".cmd")
    except KeyError:
        m_cp(output_files['ST-CMD'],                  "startup", basename + ".cmd")

    try:
        m_cp(output_files['AUTOSAVE-ST-TEST-CMD'],    "startup", basename + "-test.cmd")
    except KeyError:
        try:
            m_cp(output_files['ST-TEST-CMD'],         "startup", basename + "-test.cmd")
        except KeyError:
            pass

    req_files    = []
    try:
        m_cp(output_files['AUTOSAVE'],       "misc",    basename + ".req")
        req_files.append(basename + ".req")
    except KeyError:
        pass

    try:
        m_cp(output_files['AUTOSAVE-TEST'],       "misc",    basename + "-test.req")
        req_files.append(basename + "-test.req")
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
                eem_files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
                z.close()
        except:
            helpers.rmdirs(os.path.join(miscdir, "ccdb"))
            print "Cannot copy CCDB dump to EEE module"

    #
    # Generate Makefile
    #
    with open(os.path.join(out_mdir, "Makefile"), "w") as makefile:
        eem_files.append(makefile.name)
        future_print("""include ${EPICS_ENV_PATH}/module.Makefile

USR_DEPENDENCIES += s7plc_comms""", file = makefile)
        if len(req_files):
            future_print("USR_DEPENDENCIES += autosave", file = makefile)
            future_print("MISCS = ${{AUTOMISCS}} $(addprefix misc/, {req_files})".format(req_files = " ".join(req_files)), file = makefile)


    output_files['EEM'] = eem_files

    print "Module created: " + out_mdir
    return out_mdir


def banner():
        print " _____  _      _____   ______         _                    "
        print "|  __ \| |    / ____| |  ____|       | |                   "
        print "| |__) | |   | |      | |__ __ _  ___| |_ ___  _ __ _   _  "
        print "|  ___/| |   | |      |  __/ _` |/ __| __/ _ \| '__| | | | "
        print "| |    | |___| |____  | | ( (_| | (__| |( (_) | |  | |_| | "
        print "|_|    |______\_____| |_|  \__,_|\___|\__\___/|_|   \__, | "
        print "                                                     __/ | "
        print "European Spallation Source, Lund                    |___/ \n"



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
        parser.add_argument(
                            '--plc-interface',
                            dest    = "plc_interface",
                            help    = 'use the default templates for PLCs and generate interface PLC comms and diagnostics code',
                            metavar = 'TIA-Portal-version',
                            nargs   = "?",
                            const   = 'TIAv14',
                            type    = str
                           )

        parser.add_argument(
                            '--plc-direct',
                            dest    = "plc_direct",
                            help    = 'use the default templates for PLCs and generate direct PLC comms and diagnostics code',
                            metavar = 'TIA-Portal-version',
                            nargs   = "?",
                            const   = 'TIAv14',
                            type    = str
                           )

        parser.add_argument(
                            '--plc-beckhoff',
                            dest    = "beckhoff",
                            help    = 'use the default templates for Beckhoff PLCs and generate interface Beckhoff PLC comms',
                            metavar = 'Beckhoff-version',
                            nargs   = "?",
                            const   = 'not-used',
                            type    = str
                           )

        parser.add_argument(
                            '--list-templates',
                            dest    = "list_templates",
                            help    = "give a list of the possible templates that can be generated on-the-fly from an interface definition",
                            action  = "store_true"
                           )

        return parser


    def add_eee_arg(parser, device):
        if device:
            device = helpers.sanitizeFilename(device.lower())
        parser.add_argument(
                            '--eee',
                            '--eem',
                            dest    = "eem",
                            help    = "create a minimal EEE module with EPICS-DB and startup snippet",
                            metavar = "modulename",
                            nargs   = "?",
                            type    = str,
                            const   = device
                           )

        return parser



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
        print tf.available_printers()
        exit(0)

    if args.plc_direct is not None:
        tia_version        = args.plc_direct.lower()
        tia_map            = "TIA-MAP-DIRECT"
        args.plc_direct    = True
        args.plc_interface = False
    elif args.plc_interface is not None:
        tia_version        = args.plc_interface.lower()
        tia_map            = "TIA-MAP-INTERFACE"
        args.plc_interface = True
        args.plc_direct    = False
    else:
        tia_version = None

    beckhoff = args.beckhoff

    if tia_version is not None:
        tia13 = set({"13", "v13", "tia13", "tiav13"})
        tia14 = set({"14", "v14", "tia14", "tiav14"})

        if tia_version in tia13:
            tia_version = 13
        elif tia_version in tia14:
            tia_version = 14
        else:
            raise PLCFArgumentError(1, "Invalid TIA version: " + tia_version)

    # Second pass
    #  get EEE module name
    add_eee_arg(parser, device)

    args = parser.parse_known_args(argv)[0]

    if args.eem:
        eem = args.eem.lower()
        if eem.startswith('m-epics-'):
            eem = eem[len('m-epics-'):]
    else:
        eem = None

    # Third pass
    #  get all options
    parser         = PLCFArgumentParser()

    add_common_parser_args(parser)
    add_eee_arg(parser, device)

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

    parser.add_argument(
                        '--ccdb-test',
                        '--test',
                        dest     = "ccdb_test",
                        help     = 'select CCDB test database',
                        action   = 'store_true',
                        required = False)

    # this argument is just for show as the corresponding value is
    # set to True by default                        
    parser.add_argument(
                        '--production',
                        help     = 'select production database',
                        action   = 'store_true',
                        required = False)

    parser.add_argument(
                        '--ccdb',
                        dest     = "ccdb",
                        help     = 'use a CCDB dump as backend',
                        metavar  = 'directory-to-CCDB-dump / name-of-.ccdb.zip',
                        type     = str,
                        required = False)

    parser.add_argument(
                        '--plc-no-diag',
                        dest     = "plc_no_diag",
                        help     = 'do not generate PLC diagnostics code (if used with --plc-x)',
                        action   = 'store_true',
                        required = False)

    parser.add_argument(
                        '--plc-only-diag',
                        dest     = "plc_only_diag",
                        help     = 'generate PLC diagnostics code only (if used with --plc-x)',
                        action   = 'store_true',
                        required = False)

    parser.add_argument(
                        '--cached',
                        dest     = "clear_templates",
                        help     = 'do not clear "templates" folder; use the templates downloaded by a previous run',
                        # be aware of the inverse logic between the meaning of the option and the meaning of the variable
                        default  = True,
                        action   = 'store_false')

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '+',
                        type     = str,
                        default  = [],
                        required = not (tia_version or eem or beckhoff))

    # retrieve parameters
    args       = parser.parse_args(argv)

    start_time     = time.time()

    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    if args.root is not None:
        glob.root_installation_slot = args.root
    else:
        glob.root_installation_slot = device


    default_printers = set(["DEVICE-LIST"])

    if args.plc_interface:
        default_printers.update( [ "EPICS-DB", "IFA", tia_map ] )

    if args.plc_direct:
        tf.optimize_s7db(True)
        default_printers.update( [ "EPICS-DB", "IFA", tia_map ] )

    if beckhoff:
        default_printers.update( [ "EPICS-DB", "IFA" ] )
        global plc_type
        plc_type = "BECKHOFF"

    if eem:
        default_printers.update( [ "EPICS-DB", "AUTOSAVE-ST-CMD", "AUTOSAVE" ] )

    if default_printers:
        if not default_printers <= set(tf.available_printers()):
            print "Your PLCFactory does not support generating the following necessary templates: ", list(default_printers - set(tf.available_printers()))
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

        # TIA-MAP-DIRECT and TIA-MAP-INTERFACE are incompatible
        if "TIA-MAP-INTERFACE" in templateIDs:
            raise PLCFArgumentError("Cannot use TIA-MAP-DIRECT and TIA-MAP-INTERFACE at the same time. They are incompatible.")

    if args.plc_no_diag and args.plc_only_diag:
        raise PLCFArgumentError("--plc-no-diag and --plc-only-diag are mutually exclusive")

    if args.plc_only_diag and tia_version is None:
        raise PLCFArgumentError('--plc-only-diag requires --plc-direct or --plc-interface')

    if args.plc_only_diag and beckhoff:
        raise PLCFArgumentError('PLCFactory cannot (yet?) generate diagnostics code for Beckhoff PLCs')

    if beckhoff and ( "TIA-MAP-DIRECT" in templateIDs or "TIA-MAP-INTERFACE" in templateIDs ):
        raise PLCFArgumentError("Cannot use --plc-beckhoff with TIA-MAPs")

    if "EPICS-DB" in templateIDs:
        templateIDs.add("UPLOAD-PARAMS")

    if eem and "EPICS-TEST-DB" in templateIDs:
        templateIDs.add("ST-TEST-CMD")

    if eem and "AUTOSAVE" in templateIDs:
        templateIDs.add("AUTOSAVE-ST-CMD")

    if eem and "AUTOSAVE-TEST" in templateIDs:
        templateIDs.add("AUTOSAVE-ST-TEST-CMD")

    if "ST-CMD" in templateIDs and "AUTOSAVE-ST-CMD" in templateIDs:
        templateIDs.remove("ST-CMD")

    if "ST-TEST-CMD" in templateIDs and "AUTOSAVE-ST-TEST-CMD" in templateIDs:
        templateIDs.remove("ST-TEST-CMD")

    os.system('clear')

    banner()

    if args.ccdb:
        from cc import CC
        glob.ccdb = CC.load(args.ccdb)
    elif args.ccdb_test:
        from ccdb import CCDB_TEST
        glob.ccdb = CCDB_TEST(clear_templates = args.clear_templates)
    else:
        glob.ccdb = CCDB(clear_templates = args.clear_templates)

    global OUTPUT_DIR
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, helpers.sanitizeFilename(device.lower()))
    helpers.makedirs(OUTPUT_DIR)

    glob.modulename = eem
    processDevice(device, list(templateIDs))

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.dump("-".join([device, glob.timestamp]), OUTPUT_DIR)

    if tia_version or args.plc_only_diag:
        try:
            from InterfaceFactorySiemens import produce as ifa_produce
        except ImportError:
            print """
ERROR
=====
Siemens support is not found
"""
            exit(1)
        output_files.update(ifa_produce(OUTPUT_DIR, output_files["IFA"], output_files[tia_map], tia_version, nodiag = args.plc_no_diag, onlydiag = args.plc_only_diag, direct = args.plc_direct))

    if beckhoff:
        try:
            from InterfaceFactoryBeckhoff import produce as ifa_produce
        except ImportError:
            print """
ERROR
=====
Beckhoff support is not found
"""
            exit(1)
        output_files.update(ifa_produce(OUTPUT_DIR, output_files["IFA"], "", beckhoff))

    if eem:
        create_eem(glob.modulename)

    if args.zipit is not None:
        create_zipfile(args.zipit)

    has_warns = False
    for ifdef in ifdefs.itervalues():
        for warn in ifdef.warnings():
            if not has_warns:
                has_warns = True
                future_print("\nThe following warnings were detected:\n", file = sys.stderr)
            future_print(warn, file = sys.stderr)

    if not args.clear_templates:
        print "\nTemplates were reused\n"

    print("--- %.1f seconds ---\n" % (time.time() - start_time))




if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFArgumentError, e:
        future_print(e.message, file = sys.stderr)
        exit(e.status)
