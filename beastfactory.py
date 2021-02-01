#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import

""" Alarm Factory: Entry point """

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
import argparse
import os
import time


# Alarm Factory modules
from   beast_factory.bf_def import BEAST_DEF, BEASTDefException
from   ccdb   import CC
import helpers
import plcf_git as git

# Template Factory
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'template_factory'))
from tf_ifdef import IF_DEF




class AlarmFactoryException(Exception):
    status = 1



class AlarmFactory(object):
    etree_options = { 'encoding'        : 'utf-8',
                      'xml_declaration' : True }

    try:
        from lxml import etree
        etree_options['pretty_print'] = True
    except ImportError:
        print("""
************************************************************
*  Falling back to original ElementTree implementation.... *
*  The generated xml will NOT be 'pretty printed'          *
*                                                          *
*  Please install lxml:                                    *
*   pip install lxml                                       *
*                                                          *
************************************************************
""", file = sys.stderr)
        try:
            time.sleep(5)
        except:
            pass
        import xml.etree.ElementTree as etree


    def __init__(self, argv):
        super(AlarmFactory, self).__init__()

        if git.check_for_updates(data_dir = helpers.create_data_dir(__product__), product = "Alarm Factory"):
            return

        self._output_dir = "output"

        # get the number of --ioc arguments
        parser = AlarmArgumentParser(add_help = False)

        self.__add_source_arg(parser, False)

        args = parser.parse_known_args(argv)[0]

        self._standalone = args.iocs is None

        # build the final argument list
        parser         = AlarmArgumentParser()

        self.__add_source_arg(parser)

        def is_config_mandatory(opt):
            return opt is not None and (opt is True or (isinstance(opt, list) and len(opt) > 1))


        parser.add_argument(
                            '--config',
                            help     = 'Alarm config entry',
                            default  = None,
                            required = is_config_mandatory(args.iocs) or is_config_mandatory(args.merge_xmls)
                           )

        parser.add_argument(
                            'files',
                            metavar  = 'file',
                            help     = 'The .alarms or .xml files to use',
                            type     = str,
                            nargs    = '*'
                           )
        CC.addArgs(parser)

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

        if not self._standalone:
            if args.ccdb_test:
                from ccdb import CCDB_TEST
                self._ccdb = CCDB_TEST(clear_templates = args.clear_ccdb_cache)
            elif args.ccdb_devel:
                from ccdb import CCDB_DEVEL
                self._ccdb = CCDB_DEVEL(clear_templates = args.clear_ccdb_cache)
            else:
                self._ccdb = CC.open(args.ccdb, clear_templates = args.clear_ccdb_cache)

        if args.iocs:
            self.processIOCs(args.iocs)
        elif args.merge_xmls:
            self.mergeXMLs(args.files)
        elif args.alarm_tree:
            self.processStandalone(args.alarm_tree, args.files)
        else:
            raise AlarmArgumentError("Don't know what to do")

        if not self._standalone and not args.clear_ccdb_cache:
            print("\nAlarms definitions were reused\n")

        print("--- %.1f seconds ---\n" % (time.time() - start_time))


    def __add_source_arg(self, parser, required = True):
        sg = parser.add_argument_group('Source')
        ix = sg.add_mutually_exclusive_group(required = required)

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
                        '--merge-xmls',
                        dest     = 'merge_xmls',
                        action   = 'store_true',
                        help     = 'Merge alarm configuration xml files into one'
                       )

        ix.add_argument(
                        '--alarm-tree',
                        dest     = 'alarm_tree',
                        metavar  = 'Alarm-Tree',
                        help     = 'The alarm structure to use'
                       )


    def _makeOutputDir(self, dirname):
        output_dir = os.path.join(self._output_dir, helpers.sanitizeFilename(dirname.lower()))
        if self._device_tag:
            output_dir = os.path.join(output_dir, helpers.sanitizeFilename(CC.TAG_SEPARATOR.join([ "", "tag", self._device_tag ])))
        helpers.makedirs(output_dir)

        return output_dir


    def _downloadAlarmTree(self, ioc):
        dArtifact = ioc.downloadExternalLink("BEAST TREE", ".alarm-tree", filetype = "Alarm tree", device_tag = self._device_tag)
        if dArtifact is None:
            raise AlarmFactoryException("No alarm tree found")

        alarm_tree = dArtifact.saved_as()
        print("Parsing {} of {}".format(alarm_tree, ioc.name()))

        return alarm_tree


    def _parseAlarmTree(self, alarm_tree, merge_with = None):
        # initialize beast definition parser
        beast_def = BEAST_DEF(merge_with)

        # parse alarm tree
        self._config = beast_def.parse_alarm_tree(alarm_tree, self._config)
        print()

        return beast_def


    def _parseAlarms(self, beast_def, device):
        dArtifact = device.downloadExternalLink("BEAST TEMPLATE", ".alarms-template", filetype = "Alarm definition template", device_tag = self._device_tag)
        if dArtifact:
            alarm_list = dArtifact.saved_as()
            print("Parsing {} of {}".format(alarm_list, device.name()))
            beast_def.parse(alarm_list, device = device)
            print()

        dArtifact = device.downloadExternalLink("BEAST", ".alarms", filetype = "Alarm definition", device_tag = self._device_tag)
        if dArtifact:
            alarm_list = dArtifact.saved_as()
            print("Parsing {} of {}".format(alarm_list, device.name()))
            beast_def.parse(alarm_list, device = device)
            print()


    def _parseIfDef(self, device):
        if self._def_alarms is None:
            return

        dArtifact = device.downloadArtifact(".def", self._device_tag, filetype = "Interface Definition")
        if dArtifact is None:
            # No 'file' artifact found, let's see if there is a URL
            dArtifact = device.downloadExternalLink("EPI", ".def", filetype = "Interface Definition", device_tag = self._device_tag)
            if dArtifact is None:
                return

        ifdef = IF_DEF.parse(dArtifact, QUIET = True)

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
        alarm_tree = self._downloadAlarmTree(ioc)
        beast_def = self._parseAlarmTree(alarm_tree, merge_with)

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
            for component in item.components().values():
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
            print("""The following {} Interface Definition alarms are not added to the Alarm Configuration:
""".format(len(self._def_alarms)))
            print(self._def_alarms)


    def _comment_keywords(self):
        branch = git.get_current_branch()
        repo = helpers.url_strip_user(git.get_origin())
        commit = git.get_local_ref(branch)

        return { 'branch' : branch,
                 'repo'   : repo,
                 'commit' : commit,
               }


    def _toxml(self, beast_def):
        beast_xml = beast_def.toxml(etree = self.etree, **self._comment_keywords())

        return beast_xml


    def processIOCs(self, iocs):
        beast_def = None
        for iocName in iocs:
            beast_def = self._processIOC(iocName, beast_def)

        beast_xml = self._toxml(beast_def)

        if len(iocs) == 1:
            self._config = beast_xml.getroot().attrib["name"]

        self.writeXml(beast_xml, self._makeOutputDir(self._config))

        self._checkAlarms(beast_def)


    def _processXML(self, xml, merge_with = None):
        # initialize beast definition parser
        beast_def = BEAST_DEF(merge_with)

        # parse XML
        self._config = beast_def.fromxml(xml, self._config)
        print()

        return beast_def


    def mergeXMLs(self, xmls):
        beast_def = None
        for xml in xmls:
            beast_def = self._processXML(xml, beast_def)

        beast_xml = self._toxml(beast_def)

        self.writeXml(beast_xml)


    def processStandalone(self, alarm_tree, alarms_list):
        beast_def = self._parseAlarmTree(alarm_tree)
        for alarms in alarms_list:
            # parse alarm list
            beast_def.parse(alarms)

        beast_xml = self._toxml(beast_def)

        self.writeXml(beast_xml)


    def writeXml(self, beast_xml, directory = "."):
        with open(os.path.join(directory, self._config + ".xml"), "wb") as f:
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



class AlarmArgumentError(AlarmFactoryException):
    def __init__(self, status, message = None):
        if message is None:
            if isinstance(status, str):
                message = status
                status = 1

        super(AlarmArgumentError, self).__init__(message)
        self.status  = status


class AlarmArgumentParser(argparse.ArgumentParser):
    def __init__(self, **keyword_params):
        argparse.ArgumentParser.__init__(self, **keyword_params)


    def exit(self, status = 0, message = None):
        raise AlarmArgumentError(status, message)




if __name__ == "__main__":
    try:
        AlarmFactory(sys.argv[1:])
    except (AlarmFactoryException, BEASTDefException) as e:
        if e.status:
            print(e, file = sys.stderr)
        try:
            exit(e.status)
        except:
            exit(1)
