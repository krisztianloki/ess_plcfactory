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

# PLC Factory modules
import plcf_glob as glob
import plcf
import processTemplate as pt
from   ccdb import CCDB
from   future_print import future_print

# Template Factory
parent_dir = os.path.abspath(os.path.dirname(__file__))
tf_dir     = os.path.join(parent_dir, 'template_factory')
sys.path.append(tf_dir)
del parent_dir
del tf_dir

import tf


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

    template = None
    for artefact in artefacts:
        if not artefact.endswith(IFDEF_TAG):
            continue
        template = artefact
        break

    if template is None:
        return None

    filename = getArtefact(deviceType, template)
    if filename is None:
        return None

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

    # get artifact names of files attached to the root device
    (deviceType, rootArtefacts) = getArtefactNames(device)

    # find devices this device controls
    controls = buildControlsList(device)

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
    for f in output_files.itervalues():
        if f is not None:
            z.write(f, os.path.basename(f))
    z.close()

    print "Zipfile created: " + zipit
    return zipit


def create_eem(device):
    basename = CCDB.sanitizeFilename(device.lower())
    mdir     = "-".join(["m-epics", basename])
    out_mdir = os.path.join(OUTPUT_DIR, mdir)
    makedirs(out_mdir)

    with open(os.path.join(out_mdir, "Makefile"), "w") as makefile:
        future_print("""include ${EPICS_ENV_PATH}/module.Makefile

USR_DEPENDENCIES = s7plc_comms
""", file = makefile)

    from shutil import copy2
    def m_cp(f, d, newname):
        od = os.path.join(out_mdir, d)
        makedirs(od)
        copy2(f, os.path.join(od, newname))

    m_cp(output_files['EPICS-DB'],  "db",      basename + ".db")
    m_cp(output_files['ST-CMD'],    "startup", basename + ".cmd")
    if output_files['CCDB-DUMP'] is not None:
        import zipfile
        z = zipfile.ZipFile(output_files['CCDB-DUMP'], "r")
        z.extractall(os.path.join(out_mdir, "misc"))

    print "Module created: " + out_mdir
    return out_mdir


def main(argv):
    parser         = argparse.ArgumentParser(add_help = False)

    parser.add_argument(
                        '--plc',
                        dest = "plc",
                        help = 'use the default templates for PLCs',
                        action = "store_true"
                       )

    parser.add_argument(
                        '--eee',
                        '--eem',
                        dest    = "eem",
                        help    = "create a minimal EEE module with EPICS-DB and startup snippet",
                        action  = "store_true"
                       )

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        const    = None
                        )

    args = parser.parse_known_args(argv)[0]

    plc    = args.plc
    eem    = args.eem
    device = args.device

    parser         = argparse.ArgumentParser()

    parser.add_argument(
                        '--plc',
                        dest   = "plc",
                        help   = 'use the default templates for PLCs',
                        action = "store_true"
                       )

    parser.add_argument(
                        '--eee',
                        '--eem',
                        dest    = "eem",
                        help    = "create a minimal EEE module with EPICS-DB and startup snippet",
                        action  = "store_true"
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
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        required = True
                        )

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '*',
                        type     = str,
                        default  = [],
                        required = not (plc or eem))

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

    default_printers = []
    def add_to_default_printers(new_list):
        default_printers.extend([ p for p in new_list if p not in default_printers])

    if plc:
        add_to_default_printers( [ "EPICS-DB", "IFA", "TIA-MAP-NG", "DIAG" ] )
    if eem:
        add_to_default_printers( [ "EPICS-DB", "ST-CMD" ] )

    if default_printers:
        if not set(default_printers) <= set(tf.available_printers()):
            print "Your PLCFactory does not support generating the following necessary templates: ", list(set(default_printers) - set(tf.available_printers()))
            exit(1)

        templateIDs = default_printers + [ t for t in args.template if t not in default_printers ]
    else:
        templateIDs = args.template

    os.system('clear')

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
    makedirs(OUTPUT_DIR)

    processDevice(device, templateIDs)

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.dump("-".join([device, glob.timestamp]), OUTPUT_DIR)

    if args.zipit is not None:
        create_zipfile(args.zipit)

    if eem:
        create_eem(device)

    print("--- %.1f seconds ---\n" % (time.time() - start_time))




if __name__ == "__main__":
    main(sys.argv[1:])
