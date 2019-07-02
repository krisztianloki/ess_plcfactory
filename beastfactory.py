#!/usr/bin/env python2

from __future__ import print_function
from __future__ import absolute_import

""" BEAST Factory: Entry point """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019, European Spallation Source, Lund"
__credits__    = [ "Krisztian Loki"
                 , "Miklos Boros"
                 ]
__license__    = "GPLv3"
__maintainer__ = "Krisztian Loki"
__email__      = "krisztian.loki@esss.se"
__status__     = "Production"
__env__        = "Python version 2.7"
__product__    = "ics_beast_factory"

# Python libraries
import sys
if sys.version_info.major != 2:
    raise RuntimeError("BEASTFactory supports Python-2.x only. You are running " + sys.version)

import argparse
import os
import time


# BEAST Factory modules
from   beast_factory.bf_def import BEAST_DEF, BEASTDefException
from   ccdb   import CCDB
import helpers
import plcf_git as git

# Template Factory
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'template_factory'))
from tf_ifdef import IF_DEF




class BEASTFactoryException(Exception):
    status = 1



class BEASTFactory(object):
    etree_options = { 'encoding'        : 'utf-8',
                      'xml_declaration' : True }

    try:
        from lxml import etree
        etree_options['pretty_print'] = True
    except ImportError:
        print("Falling back to original ElementTree implementation....", file = sys.stderr)
        import xml.etree.ElementTree as etree


    def __init__(self, argv):
        if git.check_for_updates(data_dir = helpers.create_data_dir(__product__), product = "BEAST Factory"):
            return

        self._output_dir = "output"

        # get the number of --ioc arguments
        parser = PLCFArgumentParser(add_help = False)

        self.__add_ioc_arg(parser, False)

        args = parser.parse_known_args(argv)[0]

        # build the final argument list
        parser         = PLCFArgumentParser()

        self.__add_ioc_arg(parser)

        def is_config_mandatory(opt):
            return opt is not None and len(opt) > 1


        parser.add_argument(
                            '--config',
                            help     = 'BEAST config entry',
                            default  = None,
                            required = is_config_mandatory(args.iocs) or is_config_mandatory(args.xmls)
                           )

        CCDB.addArgs(parser)

        parser.add_argument(
                            '--tag',
                            help     = 'tag to use if more than one matching External Link is found',
                            type     = str
                           )

        parser.add_argument(
                            '--verify',
                            help     = 'try to verify PV names using Interface Definition files',
                            action   = 'store_true'
                           )

        # retrieve parameters
        args = parser.parse_args(argv)

        start_time = time.time()

        self._config     = args.config
        self._device_tag = args.tag
        self._def_alarms = list() if args.verify else None

        os.system('clear')

        banner()

        if args.ccdb:
            from cc import CC
            self._ccdb = CC.load(args.ccdb)
        elif args.ccdb_test:
            from ccdb import CCDB_TEST
            self._ccdb = CCDB_TEST(clear_templates = args.clear_ccdb_cache)
        elif args.ccdb_devel:
            from ccdb import CCDB_DEVEL
            self._ccdb = CCDB_DEVEL(clear_templates = args.clear_ccdb_cache)
        else:
            self._ccdb = CCDB(clear_templates = args.clear_ccdb_cache)

        if args.iocs:
            self.processIOCs(args.iocs)
        elif args.xmls:
            self.mergeXMLs(args.xmls)

        if not args.clear_ccdb_cache:
            print("\nAlarms definitions were reused\n")

        print("--- %.1f seconds ---\n" % (time.time() - start_time))


    def __add_ioc_arg(self, parser, required = True):
        ix = parser.add_mutually_exclusive_group(required = required)

        ix.add_argument(
                        '--ioc',
                        '-d',
                        '--device',
                        dest     = 'iocs',
                        metavar  = 'IOC-name',
                        help     = 'IOC / installation slot',
                        action   = "append",
                       )


        ix.add_argument(
                        '--xml',
                        dest     = 'xmls',
                        metavar  = 'BEAST-xml-file',
                        help     = 'BEAST xml files to merge',
                        action   = "append",
                       )


    def _makeOutputDir(self, dirname):
        output_dir = os.path.join(self._output_dir, helpers.sanitizeFilename(dirname.lower()))
        if self._device_tag:
            output_dir = os.path.join(output_dir, helpers.sanitizeFilename(CCDB.TAG_SEPARATOR.join([ "", "tag", self._device_tag ])))
        helpers.makedirs(output_dir)

        return output_dir


    def _parseAlarmTree(self, ioc, merge_with):
        alarm_tree = ioc.downloadExternalLink("BEAST TREE", ".alarm-tree", filetype = "Alarm tree", device_tag = self._device_tag)
        if alarm_tree is None:
            raise BEASTFactoryException("No alarm tree found")

        print("Parsing {} of {}".format(alarm_tree, ioc.name()))

        # initialize beast definition parser
        beast_def = BEAST_DEF(merge_with)

        # parse alarm tree
        beast_def.parse_alarm_tree(alarm_tree, self._config)
        print()

        return beast_def


    def _parseAlarms(self, beast_def, device):
        alarm_list = device.downloadExternalLink("BEAST TEMPLATE", ".alarms-template", filetype = "Alarm definition template", device_tag = self._device_tag)
        if alarm_list:
            print("Parsing {} of {}".format(alarm_list, device.name()))
            beast_def.parse(alarm_list, device = device)
            print()

        alarm_list = device.downloadExternalLink("BEAST", ".alarms", filetype = "Alarm definition", device_tag = self._device_tag)
        if alarm_list:
            print("Parsing {} of {}".format(alarm_list, device.name()))
            beast_def.parse(alarm_list, device = device)
            print()


    def _parseIfDef(self, device):
        if self._def_alarms is None:
            return

        filename = device.downloadArtifact(".def", self._device_tag, filetype = "Interface Definition")
        if filename is None:
            # No 'file' artifact found, let's see if there is a URL
            filename = device.downloadExternalLink("EPI", ".def", filetype = "Interface Definition", device_tag = self._device_tag)
            if filename is None:
                return

        ifdef = IF_DEF.parse(filename, QUIET = True)

        self._def_alarms.extend(map(lambda a: "{}:{}".format(device.name(), a.pv_name()), ifdef.alarms()))


    def _processIOC(self, iocName, merge_with = None):
        # clear any previous CCDB data
        self._ccdb.clear()

        # create a stable list of controlled devices
        try:
            print("Obtaining controls tree...", end = '', flush = True)
        except TypeError:
            print("Obtaining controls tree...", end = '')
            sys.stdout.flush()

        # get IOC device
        ioc = self._ccdb.device(iocName)

        devices = ioc.buildControlsList(include_self = True, verbose = True)

        # parse alarm tree
        beast_def = self._parseAlarmTree(ioc, merge_with)

        for device in devices:
            # parse alarm list
            self._parseAlarms(beast_def, device)
            # parse IfDef
            self._parseIfDef(device)

        # create a dump of CCDB
        self._ccdb.save(iocName, self._makeOutputDir(iocName))

        return beast_def


    def _checkAlarms(self, bf_def):
        if self._def_alarms is None:
            return

        extra_alarms = list()
        def check_pvs(item):
            for component in item.components().itervalues():
                for pv in component.pvs():
                    try:
                        self._def_alarms.remove(pv.name())
                    except ValueError:
                        extra_alarms.append(pv.name())

                check_pvs(component)

        check_pvs(bf_def)

        if extra_alarms:
            print("""The following alarms could not be found in Interface Definition files:
""")
            print(extra_alarms)

        if self._def_alarms:
            print("""The following {} Interface Definition alarms are not added to BEAST:
""".format(len(self._def_alarms)))
            print(self._def_alarms)


    def __beastXML(self):
        beast_xml = self.etree.ElementTree(self.etree.Element('config'))
        root      = beast_xml.getroot()
        root.tag  = "config"
        root.attrib.clear()
        root.attrib['name'] = self._config

        return (beast_xml, root)


    def processIOCs(self, iocs):
        beast_def = None
        for iocName in iocs:
            beast_def = self._processIOC(iocName, beast_def)

        branch = git.get_current_branch()
        beast_xml = beast_def.toxml(etree = self.etree, branch = branch, commit = git.get_local_ref(branch))

        if len(iocs) == 1:
            self._config = beast_xml.getroot().attrib["name"]

        self.writeXml(beast_xml)

        self._checkAlarms(beast_def)


    def mergeXMLs(self, xmls):
        (beast_xml, root) = self.__beastXML()
        for xml in xmls:
            for component in self.etree.parse(xml).getroot():
                root.append(component)

        self.writeXml(beast_xml)


    def writeXml(self, beast_xml):
        with open(os.path.join(self._makeOutputDir(self._config), self._config + ".xml"), "w") as f:
            print("""
Generating output file {}...
""".format(f.name))
            beast_xml.write(f, **self.etree_options)




def banner():
    print(" ____  ______           _____ _______   ______         _                   ")
    print("|  _ \|  ____|   /\    / ____|__   __| |  ____|       | |                  ")
    print("| |_) | |__     /  \  | (___    | |    | |__ __ _  ___| |_ ___  _ __ _   _ ")
    print("|  _ <|  __|   / /\ \  \___ \   | |    |  __/ _` |/ __| __/ _ \| '__| | | |")
    print("| |_) | |____ / ____ \ ____) |  | |    | | ( (_| | (__| |( (_) | |  | |_| |")
    print("|____/|______/_/    \_\_____/   |_|    |_|  \__,_|\___|\__\___/|_|   \__, |")
    print("                                                                      __/ |")
    print("                                                                     |___/ ")
    print("European Spallation Source, Lund\n")



class PLCFArgumentError(Exception):
    def __init__(self, status, message = None):
        self.status  = status
        self.message = message


class PLCFArgumentParser(argparse.ArgumentParser):
    def __init__(self, **keyword_params):
        argparse.ArgumentParser.__init__(self, **keyword_params)


    def exit(self, status = 0, message = None):
        if message:
            self._print_message(message, sys.stderr)

        raise PLCFArgumentError(status)




if __name__ == "__main__":
    try:
        BEASTFactory(sys.argv[1:])
    except PLCFArgumentError as e:
        print(e.message, file = sys.stderr)
        exit(e.status)
    except (BEASTFactoryException, BEASTDefException) as e:
        print(e, file = sys.stderr)
        try:
            exit(e.status)
        except:
            exit(1)
