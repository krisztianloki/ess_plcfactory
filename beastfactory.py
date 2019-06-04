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

        parser         = PLCFArgumentParser()

        parser.add_argument(
                            '-d',
                            '--device',
                            '--ioc',
                            dest     = 'ioc',
                            help     = 'IOC / installation slot',
                            required = True
                            )

        parser.add_argument(
                            '--config',
                            help     = 'BEAST config entry',
                            default  = None
                           )

        CCDB.addArgs(parser)

        parser.add_argument(
                            '--tag',
                            help     = 'tag to use if more than one matching External Link is found',
                            type     = str)

        # retrieve parameters
        args = parser.parse_args(argv)

        start_time = time.time()

        self._iocName    = args.ioc
        self._config     = args.config
        self._device_tag = args.tag

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

        self._output_dir = os.path.join(self._output_dir, helpers.sanitizeFilename(self._iocName.lower()))
        if self._device_tag:
            self._output_dir = os.path.join(self._output_dir, helpers.sanitizeFilename(CCDB.TAG_SEPARATOR.join([ "", "tag", self._device_tag ])))
        helpers.makedirs(self._output_dir)

        self.processIOC()

        if not args.clear_ccdb_cache:
            print("\nAlarms definitions were reused\n")

        print("--- %.1f seconds ---\n" % (time.time() - start_time))


    def parseAlarmTree(self, ioc):
        alarm_tree = ioc.downloadExternalLink("BEAST TREE", ".alarm-tree", filetype = "Alarm tree", device_tag = self._device_tag)
        if alarm_tree is None:
            raise BEASTFactoryException("No alarm tree found")

        self._beast_def.parse_alarm_tree(alarm_tree)
        self._alarm_tree = self.etree.ElementTree(self.etree.Element('config'))
        root = self._alarm_tree.getroot()
        for component in self._beast_def.components().itervalues():
            component.xml(root, etree = self.etree)

#        # Has to do this for pretty_print to work
#        for element in root.iter():
#            element.tail = None
#            element.text = None

        if root.tag == "config":
            self._config = root.attrib.get("name", self._config)
        if not self._config:
            raise BEASTFactoryException("No config name is defined in alarm tree and no --config option was specified")

        root.tag    = "config"
        root.attrib.clear()
        root.attrib['name'] = self._config


    def parseAlarms(self, device):
        alarm_list = device.downloadExternalLink("BEAST TEMPLATE", ".alarms-template", filetype = "Alarm definition template", device_tag = self._device_tag)
        if alarm_list:
            print("Parsing {} of {}".format(alarm_list, device.name()))
            self._beast_def.parse(alarm_list, device = device)

        alarm_list = device.downloadExternalLink("BEAST", ".alarms", filetype = "Alarm definition", device_tag = self._device_tag)
        if alarm_list:
            print("Parsing {} of {}".format(alarm_list, device.name()))
            self._beast_def.parse(alarm_list, device = device)


    def _process_component(self, components):
        for component in components.itervalues():
            xml_component = self._alarm_tree.getroot().find('.' + component.xpath())
            if xml_component is None:
                raise BEASTFactoryException("Component '{}' (line {}) at {} is not defined in the alarm tree".format(component.name(),
                                                                                                                     component.lineno(),
                                                                                                                     component.path()))

            for pv in component.pvs():
                pv.xml(xml_component, etree = self.etree)

            self._process_component(component.components())


    def processIOC(self):
        ioc = self._ccdb.device(self._iocName)

        self._beast_def = BEAST_DEF()

        # parse alarm tree
        self.parseAlarmTree(ioc)

        # create a stable list of controlled devices
        try:
            print("Obtaining controls tree...", end = '', flush = True)
        except TypeError:
            print("Obtaining controls tree...", end = '')
            sys.stdout.flush()

        devices = ioc.buildControlsList(include_self = True, verbose = True)

        for device in devices:
            # parse alarm list
            self.parseAlarms(device)

        if self._beast_def:
            self._process_component(self._beast_def.components())

        with open(os.path.join(self._output_dir, self._config + ".xml"), "w") as beast_xml:
            print("""
Generating output file {}...
""".format(beast_xml.name))
            self._alarm_tree.write(beast_xml, **self.etree_options)

        # create a dump of CCDB
        self._ccdb.dump(self._iocName, self._output_dir)




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
    def __init__(self):
        argparse.ArgumentParser.__init__(self)


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
