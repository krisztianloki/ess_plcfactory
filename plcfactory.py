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

# global variables
TEMPLATE_DIR = "templates"
OUTPUT_DIR   = "output"
TEMPLATE_TAG = "TEMPLATE"
IFDEF_TAG    = ".def"
hashobj      = hashlib.sha256()
ifdefs       = dict()
output_files = dict()


def getArtefact(deviceType, filename):
    return glob.ccdb.getArtefact(deviceType, filename, TEMPLATE_DIR)


def openArtefact(deviceType, filenames, tag, templateID):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(tag,        str )
    assert isinstance(templateID, str )

    lines = []

    for filename in filenames:
        if matchingArtefact(filename, tag, templateID):
            filename = getArtefact(deviceType, filename)

            if filename is None:
                break

            with open(filename) as f:
                lines = f.readlines()

            break

    return lines


def getTemplateName(deviceType, filenames, templateID):
    assert isinstance(deviceType, str )
    assert isinstance(filenames,  list)
    assert isinstance(templateID, str )

    result = None

    for filename in filenames:

        if matchingArtefact(filename, TEMPLATE_TAG, templateID):

            # download template and save in template directory
            result = getArtefact(deviceType, filename)

            break

    return result


def matchingArtefact(filename, tag, templateID):
    assert isinstance(filename,   str)
    assert isinstance(tag,        str)
    assert isinstance(templateID, str)

    # attached artefacts may be of different file types, e.g. PDF
    if not filename.endswith('.txt') or tag not in filename:
        return False

    # exactly one '.' in filename
    assert filename.count('.') == 1, filename

    filename = filename.split('.')[0] # removing '.txt.
    tmp      = filename.split("_")    # separating fields in filename

    # extract template ID
    name     = tmp[-1]

    return name == templateID


def createFilename(header, device, templateID, deviceType):
    assert isinstance(header,     list)
    assert isinstance(device,     str )
    assert isinstance(templateID, str )
    assert isinstance(deviceType, str )

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if len(header) == 0 or tagPos == -1:

        outputFile = device + "_" + deviceType + "_template-" + templateID \
                   + "_" + glob.timestamp + ".scl"

        return CCDB.sanitizeFilename(outputFile)

    else:

        filename = header[tagPos]

        # remove tag and strip surrounding whitespace
        filename = filename[len(tag):].strip()
        filename = plcf.keywordsHeader(filename, device, templateID)

        return CCDB.sanitizeFilename(filename)


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


def getArtefactNames(device):
    assert isinstance(device, str)

    # get artifact names of files attached to a device
    deviceType = glob.ccdb.getDeviceType(device)
    artefacts  = glob.ccdb.getArtefactNames(device)

    return (deviceType, artefacts)


def deviceTypeToFilename(deviceType):
    return glob.ccdb.sanitizeFilename(deviceType)


def getIfDefFromURL(device, deviceType):
    url = glob.ccdb.getArtefactURL(device, "EPI")
    if url is None:
        return None

    filename = deviceTypeToFilename(deviceType).upper() + ".def"
    url = "/".join([ url, "raw/master", filename ])

    print "Trying to download Interface Definition file from", url

    return glob.ccdb.getArtefactFromURL(url, deviceType, filename, TEMPLATE_DIR)


#
# Returns an interface definition object
#
def getIfDef(device):
    assert isinstance(device, str)

    deviceType = glob.ccdb.getDeviceType(device)

    if deviceType in ifdefs:
        print "Device type: " + deviceType

        return ifdefs[deviceType]

    artefacts = glob.ccdb.getArtefactNames(device)

    template = filter(lambda ida: ida.endswith(IFDEF_TAG), artefacts)

    if len(template) > 1:
        print "More than one Interface Definiton files were found for {device}: {defs}".format(device = device, defs = template)
        exit(1)

    if len(template) == 0:
        filename = getIfDefFromURL(device, deviceType)
        if filename is None:
            return None

        template = deviceTypeToFilename(deviceType)
    else:
        filename = None
        template = template[0]


    if filename is None:
        filename = getArtefact(deviceType, template)

    if filename is None:
        print "Could not download Interface Definition file {f} for device {d}".format(f = template, d = device)
        exit(1)

    with open(filename) as f:
        ifdef = tf.processLines(f, HASH = hashobj)

    if ifdef is not None:
        print "Device type: " + deviceType

        ifdefs[deviceType] = ifdef

    return ifdef


def buildControlsList(device):
    assert isinstance(device, str)

    # find devices this device _directly_ controls
    controls = glob.ccdb.controls(device)

    print device + " controls: "

    for elem in controls:
        print "\t- " + elem

    print "\n"

    return controls


def getHeaderFooter(templateID, deviceType, artefacts):
    assert isinstance(templateID, str)
    assert isinstance(deviceType, str)
    assert isinstance(artefacts,  list)

    templatePrinter = tf.get_printer(templateID)
    if templatePrinter is not None:
        header = []
        templatePrinter.header(header)
        footer = []
        templatePrinter.footer(footer)
    else:
        header = openArtefact(deviceType, artefacts, "HEADER", templateID)
        footer = openArtefact(deviceType, artefacts, "FOOTER", templateID)

    if len(header) == 0:
        print "No header found.\n"
    else:
        print "Header read.\n"

    if len(footer) == 0:
        print "No footer found.\n"
    else:
        print "Footer read.\n"

    return (header, footer, templatePrinter)


def processTemplateID(templateID, rootDevice, rootDeviceType, rootArtefacts, controls):
    assert isinstance(templateID,      str)
    assert isinstance(rootDevice,      str)
    assert isinstance(rootDeviceType,  str)
    assert isinstance(rootArtefacts,   list)
    assert isinstance(controls,        list)

    print "#" * 60
    print "Template ID " + templateID
    print "Device at root: " + rootDevice + "\n"

    # collect lines to be written at the end
    output = []

    # process header/footer
    (header, footer, templatePrinter) = getHeaderFooter(templateID, rootDeviceType, rootArtefacts)

    print "Processing entire tree of controls-relationships:\n"

    # for each device, find corresponding template and process it
    output     = []

    # starting with devices controlled by the root device
#    toProcess  = controls[::-1]  # reverse the list (_NOT_ in-place) so that pop will actually give elements in the right order
    toProcess  = list(controls)
    processed  = set()
    outputFile = os.path.join(OUTPUT_DIR, createFilename(header, rootDevice, templateID, rootDeviceType))

    if len(header):
        header = pt.process(rootDevice, header)

    if len(footer):
        footer = pt.process(rootDevice, footer)

    while toProcess != []:

        elem = toProcess.pop()

        if elem in processed:  # this should be redundant
            continue

        print elem

        # get template
        template = None
        if templatePrinter is not None:
            ifdef = getIfDef(elem)
            if ifdef is not None:
                template = []
                templatePrinter.body(ifdef, template)

        if template is None:
            (deviceType, artefacts) = getArtefactNames(elem)
            print "Device type: " + deviceType

            template = getTemplateName(deviceType, artefacts, templateID)

        if template is not None:
            # process template and add result to output
            output += pt.process(elem, template)
            print "Template processed."

        else:
            print "No template found."

        controls = glob.ccdb.controls(elem)

        print "This device controls: "

        if controls != None and len(controls) > 0:

            for c in controls:
                print "\t- " + c #, c in processed
                if c not in processed:
                    toProcess.append(c)

        else:
            print "N/A"

        print "=" * 40
        processed.add(elem)

    print "\n"

    # process #HASH keyword in header and footer
    header      = processHash(header)
    footer      = processHash(footer)

    eol         = getEOL(header)

    output      = header + output + footer

    if len(output) == 0:
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


def processDevice(device, templateIDs):
    assert isinstance(device,      str)
    assert isinstance(templateIDs, list)

    print "#" * 60
    print "Device at root: " + device + "\n"

    # find devices this device controls
    controls = buildControlsList(device)

    # get artifact names of files attached to the root device
    (deviceType, rootArtefacts) = getArtefactNames(device)

    map(lambda x: processTemplateID(x, device, deviceType, rootArtefacts, controls), templateIDs)


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as ose:
        if not os.path.isdir(path):
            raise


def create_zipfile(zipit):
    import zipfile

    if not zipit.endswith(".zip"):
        zipit += ".zip"

    zipit = glob.ccdb.sanitizeFilename(zipit)

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


def create_eem(device):
    eem_files = []
    basename  = CCDB.sanitizeFilename(device.lower())
    out_mdir  = os.path.join(OUTPUT_DIR, "-".join(["m-epics", basename]))
    makedirs(out_mdir)

    with open(os.path.join(out_mdir, "Makefile"), "w") as makefile:
        eem_files.append(makefile.name)
        future_print("""include ${EPICS_ENV_PATH}/module.Makefile

USR_DEPENDENCIES = s7plc_comms
""", file = makefile)

    from shutil import copy2
    def m_cp(f, d, newname):
        od = os.path.join(out_mdir, d)
        makedirs(od)
        of = os.path.join(od, newname)
        copy2(f, of)
        eem_files.append(of)

    m_cp(output_files['EPICS-DB'],       "db",      basename + ".db")
    try:
        m_cp(output_files['EPICS-TEST-DB'],  "db",      basename + "-test.db")
    except KeyError:
        pass
    m_cp(output_files['ST-CMD'],         "startup", basename + ".cmd")

    if output_files['CCDB-DUMP'] is not None:
        import zipfile
        miscdir = os.path.join(out_mdir, "misc")
        z = zipfile.ZipFile(output_files['CCDB-DUMP'], "r")
        z.extractall(miscdir)
        eem_files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
        z.close()

    output_files['EEM'] = eem_files

    print "Module created: " + out_mdir
    return out_mdir


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
                            '--plc',
                            dest    = "plc",
                            help    = 'use the default templates for PLCs and generate PLC comms and diagnostics code',
                            metavar = 'TIA-Portal-version',
                            type    = str
                           )

        parser.add_argument(
                            '--legacy-plc',
                            dest    = "legacy_plc",
                            help    = 'use the default legacy templates for PLCs',
                            action  = "store_true"
                           )

        parser.add_argument(
                            '--eee',
                            '--eem',
                            dest    = "eem",
                            help    = "create a minimal EEE module with EPICS-DB and startup snippet",
                            action  = "store_true"
                           )

        parser.add_argument(
                            '--list-templates',
                            dest    = "list_templates",
                            help    = "give a list of the possible templates that can be generated on-the-fly from an interface definition",
                            action  = "store_true"
                           )

        return parser


    parser         = argparse.ArgumentParser(add_help = False)

    add_common_parser_args(parser)

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        const    = None
                        )

    args = parser.parse_known_args(argv)[0]

    if args.list_templates:
        print tf.available_printers()
        exit(0)

    if args.plc is not None:
        plc = True
        tia13 = set({"13", "v13", "tia13", "tiav13"})
        tia14 = set({"14", "v14", "tia14", "tiav14"})

        if args.plc.lower() in tia13:
            tia_version = 13
        elif args.plc.lower() in tia14:
            tia_version = 14
        else:
            raise PLCFArgumentError(1, "Invalid TIA version: " + args.plc)
    else:
        plc = False

    legacy_plc = args.legacy_plc
    eem        = args.eem
    device     = args.device
    glob.root_installation_slot = device

    parser         = PLCFArgumentParser()

    add_common_parser_args(parser)

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
                        help     = 'do not generate PLC diagnostics code (if used with --plc)',
                        action   = 'store_true',
                        required = False)

    parser.add_argument(
                        '--plc-only-diag',
                        dest     = "plc_only_diag",
                        help     = 'generate PLC diagnostics code only (if used with --plc)',
                        action   = 'store_true',
                        required = False)

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '*',
                        type     = str,
                        default  = [],
                        required = not (plc or eem or legacy_plc))

    # retrieve parameters
    args       = parser.parse_args(argv)

    start_time     = time.time()

    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

    if args.ccdb:
        from ccdb_file import CCDB_FILE
        glob.ccdb = CCDB_FILE(args.ccdb)
    elif args.ccdb_test:
        from ccdb import CCDB_TEST
        glob.ccdb = CCDB_TEST()
    else:
        glob.ccdb = CCDB()

    default_printers = set()

    if plc:
        default_printers.update( [ "EPICS-DB", "IFA", "TIA-MAP-NG" ] )

    if legacy_plc:
        tf.optimize_s7db(True)
        default_printers.update( [ "EPICS-DB", "TIA-MAP" ] )

    if eem:
        default_printers.update( [ "EPICS-DB", "ST-CMD" ] )

    if default_printers:
        if not default_printers <= set(tf.available_printers()):
            print "Your PLCFactory does not support generating the following necessary templates: ", list(default_printers - set(tf.available_printers()))
            exit(1)

        templateIDs = default_printers | set(args.template)
    else:
        templateIDs = set(args.template)

    # Make sure that OPTIMIZE_S7DB is turned on if TIA-MAP is requested
    if "TIA-MAP" in templateIDs:
        tf.optimize_s7db(True)
        if args.plc_no_diag == False:
            args.plc_only_diag =  True
            tia_version        =  14
            templateIDs.add("IFA")

        # TIA-MAP and TIA-MAP-NG are incompatible
        if "TIA-MAP-NG" in templateIDs:
            raise PLCFArgumentParser("Cannot use TIA-MAP and TIA-MAP-NG at the same time. They are incompatible.")

    if args.plc_no_diag and args.plc_only_diag:
        raise PLCFArgumentError("--plc-no-diag and --plc-only-diag are mutually exclusive")

    if args.plc_only_diag and (not ("TIA-MAP-NG" in templateIDs or "TIA-MAP" in templateIDs) or not "IFA" in templateIDs):
        raise PLCFArgumentError('--plc-only-diag requires at least the "IFA" and one of the "TIA-MAP" or "TIA-MAP-NG" templates')

    os.system('clear')

    tia_map = "TIA-MAP-NG" if "TIA-MAP-NG" in templateIDs else "TIA-MAP"

    from shutil import rmtree
    def onrmtreeerror(func, path, exc_info):
        if path != TEMPLATE_DIR:
            raise

        if not (func is os.listdir or func is os.rmdir):
            raise

        if not exc_info[0] is OSError:
            raise

        if exc_info[1].errno != 2:
            raise

    # remove templates downloaded in a previous run
    rmtree(TEMPLATE_DIR, onerror = onrmtreeerror)

    makedirs(TEMPLATE_DIR)
    global OUTPUT_DIR
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, CCDB.sanitizeFilename(device.lower()))
    makedirs(OUTPUT_DIR)

    processDevice(device, list(templateIDs))

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.dump("-".join([device, glob.timestamp]), OUTPUT_DIR)

    if plc or args.plc_only_diag:
        from InterfaceFactory import produce as ifa_produce
        output_files.update(ifa_produce(OUTPUT_DIR, output_files["IFA"], output_files[tia_map], tia_version, nodiag = args.plc_no_diag, onlydiag = args.plc_only_diag))

    if eem:
        create_eem(device)

    if args.zipit is not None:
        create_zipfile(args.zipit)

    print("--- %.1f seconds ---\n" % (time.time() - start_time))




if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFArgumentError, e:
        future_print(e.message, file = sys.stderr)
        exit(e.status)
