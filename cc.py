from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
from   os import path     as os_path
try:
    from   urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

try:
    import requests
except ImportError:
    from sys import path as sys_path

    # add directory for third-party libraries to module search path
    parent_dir = os_path.abspath(os_path.dirname(__file__))
    lib_dir    = os_path.join(parent_dir, 'libs')
    sys_path.append(lib_dir)
    del parent_dir
    del lib_dir

    # third-party libraries, stored in folder 'libs'
    import requests


# disable printing of unsigned SSH connection warnings to console
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# PLC Factory modules
import helpers



class CC(object):
    TEMPLATE_DIR    = "templates"
    TAG_SEPARATOR   = "__"
    paths_cached    = dict()
    sessions_cached = dict()


    class Exception(Exception):
        """Base class for Controls and Configuration exceptions"""



    class DownloadException(Exception):
        def __init__(self, url, code):
            super(CC.DownloadException, self).__init__()
            self.url  = url
            self.code = code


        def __str__(self):
            return "Cannot download {url}: error {code}".format(url  = self.url,
                                                                code = self.code)



    class ArtifactException(DownloadException):
        def __init__(self, dloadexception, deviceName = None, filename = None):
            self.deviceName = deviceName
            self.filename   = filename

            if isinstance(dloadexception, CC.DownloadException):
                super(CC.ArtifactException, self).__init__(url = dloadexception.url, code = dloadexception.code)
                self.msg = "Cannot get artifact {art} of {device}: error {code} ({url})".format(device = self.deviceName,
                                                                                                art    = self.filename,
                                                                                                code   = self.code,
                                                                                                url    = self.url)
            else:
                super(CC.ArtifactException, self).__init__(None, None)
                self.msg = dloadexception


        def __str__(self):
            return self.msg



    class Artifact(object):
        # list of the path names of downloaded artifacts
        # FIXME: should make this per-CC
        downloadedArtifacts = list()

        def __init__(self, device):
            self._device = device


        def __repr__(self):
            return self.name()


        def name(self):
            raise NotImplementedError


        def is_file(self):
            raise NotImplementedError


        def is_uri(self):
            raise NotImplementedError


        def is_perdevtype(self):
            raise NotImplementedError


        def filename(self):
            raise NotImplementedError


        def uri(self):
            raise NotImplementedError


        def uniqueID(self):
            raise NotImplementedError


        # Returns: ""
        # filename is the default filename to use if not specified with '[]' notation
        def downloadExternalLink(self, filename, extension = None, git_tag = None, filetype = "External Link"):
            linkfile  = self.name()

            open_bra = linkfile.find('[')
            if open_bra != -1:
                base = linkfile[:open_bra]

                if linkfile[-1] != ']':
                    raise CC.ArtifactException("Invalid name format in External Link for {device}: {name}".format(device = self._device.name(), name = linkfile), self._device.name(), linkfile)

                filename = linkfile[open_bra + 1 : -1]
                if extension is not None:
                    if not extension.startswith('.'):
                        extension = '.{}'.format(extension)
                    if not filename.endswith(extension):
                        filename += extension

                # Check if the specified filename is valid. Need to split if path was included
                def check_filename(fname):
                    head, tail = os_path.split(fname)
                    if not head:
                        return True
                    if head != helpers.sanitizeFilename(head):
                        return False
                    return check_filename(tail)

                if not check_filename(filename):
                    raise CC.ArtifactException("Invalid filename in External Link for {device}: {name}".format(device = self._device.name(), name = filename), self._device.name(), filename)
            else:
                base = linkfile

            if git_tag is None:
                git_tag = self._device.properties().get(base + " VERSION", "master")
            url = "/".join([ "raw/{}".format(git_tag), filename ])

            print("Downloading {filetype} file {filename} (version {version}) from {url}".format(filetype = filetype,
                                                                                                 filename = filename,
                                                                                                 url      = self.uri(),
                                                                                                 version  = git_tag))

            return self.download(extra_url = url)


        # Returns: "", the downloaded filename
        def download(self, extra_url = ""):
            # NOTE: we _must not_ use CC.TEMPLATE_DIR here,
            # CCDB_Dump relies on creating an instance variant of TEMPLATE_DIR to point it to its own templates directory
            output_dir = self._device.ccdb.TEMPLATE_DIR

            if self.is_uri():
                filename = CC.urlToFilename(extra_url)
                url      = "/".join([ self.uri(), extra_url ])
                save_as  = CC.saveas(self.uniqueID(), filename, os_path.join(output_dir, CC.urlToDir(url)))
            else:
                filename = self.filename()
                url      = None
                save_as  = CC.saveas(self.uniqueID(), filename, output_dir)

            # check if filename has already been downloaded
            if os_path.exists(save_as):
                return save_as

            try:
                self._download(save_as, url = url)
            except CC.DownloadException as e:
                raise CC.ArtifactException(e, deviceName = self._device.name(), filename = filename)

            CC.Artifact.downloadedArtifacts.append(save_as)

            return save_as



    class Device(object):
        ccdb = None

        def __init__(self, ccdb):
            self._inControlledTree = False
            if ccdb is not None:
                self.ccdb = ccdb


        @staticmethod
        def _ensure(var, default):
            #
            # Do not return None
            #
            if var is not None:
                return var

            return default


        # Returns: {}
        def keys(self):
            raise NotImplementedError


        # Returns: ""
        def name(self):
            raise NotImplementedError


        def putInControlledTree(self):
            self._inControlledTree = True


        def isInControlledTree(self):
            return self._inControlledTree


        # Returns: []
        def controls(self):
            return self._ensure(self._controls(), [])


        # Returns: []
        def controlledBy(self, filter_by_controlled_tree = False):
            ctrldBy = self._ensure(self._controlledBy(filter_by_controlled_tree), [])
            if not filter_by_controlled_tree:
                return ctrldBy
            return filter(lambda d: d.isInControlledTree(), ctrldBy)


        # Returns: {}
        def properties(self):
            return self._ensure(self._properties(), [])


        # Returns: {}
        def propertiesDict(self, prefixToIgnore = True):
            return self._ensure(self._propertiesDict(), {})


        # Returns: ""
        def deviceType(self):
            return self._ensure(self._deviceType(), "")


        # Returns: ""
        def description(self):
            return self._ensure(self._description(), "")


        # Returns: []
        def artifacts(self):
            return self._ensure(self._artifacts(), [])


        # Returns: []
        def artifactNames(self):
            return map(lambda an: an.name(), filter(lambda fa: fa.is_file(), self.artifacts()))


        # Returns: []
        def externalLinks(self):
            return filter(lambda u: u.is_uri(), self.artifacts())


        # Returns: ""
        def backtrack(self, prop):
            return self._ensure(self._backtrack(prop), "")


        def defaultFilename(self, extension):
            if not extension.startswith('.'):
                extension = '.{}'.format(extension)

            return helpers.sanitizeFilename(self.deviceType().upper() + extension)


        def __splitDefs(self, defs):
            # Separate device and device type artifacts
            devtype_defs = []
            dev_defs     = []
            for art in defs:
                if art.is_perdevtype():
                    devtype_defs.append(art)
                else:
                    dev_defs.append(art)

            return (dev_defs, devtype_defs)


        # Returns the filename or None
        def downloadArtifact(self, extension, device_tag = None, filetype = ''):
            if not extension.startswith('.'):
                extension = '.{}'.format(extension)

            if device_tag:
                # whatever__devicetag.extension
                suffix = "".join([ CC.TAG_SEPARATOR, device_tag, extension ])
            else:
                suffix = extension

            defs = filter(lambda a: a.is_file() and a.filename().endswith(suffix), self.artifacts())

            # Separate device and device type artifacts
            (dev_defs, devtype_defs) = self.__splitDefs(defs)

            def __checkArtifactList(defs):
                if not defs:
                    return None

                if len(defs) > 1:
                    raise CC.ArtifactException("More than one {filetype} Artifacts were found for {device}: {defs}".format(filetype = filetype, device = self.name(), defs = defs), self.name())

                print("Downloading {filetype} file {filename} from CCDB".format(filetype = filetype,
                                                                                filename = defs[0].filename()))
                return defs[0].download()

            # device artifacts have higher priority than device type artifacts
            art = __checkArtifactList(dev_defs)
            if art is not None:
                return art

            return __checkArtifactList(devtype_defs)


        # Returns the filename or None
        def downloadExternalLink(self, base, extension, device_tag = None, filetype = 'External Link', git_tag = None):
            if not extension.startswith('.'):
                extension = '.{}'.format(extension)

            if device_tag:
                # base__devicetag
                base = CC.TAG_SEPARATOR.join([ base, device_tag ])

            fqbase = base + "["
            artifacts = filter(lambda u: u.is_uri() and (u.name() == base or u.name().startswith(fqbase)), self.artifacts())

            # Separate device and device type external links
            (dev_defs, devtype_defs) = self.__splitDefs(artifacts)

            def __checkExternalLinkList(defs):
                if not defs:
                    return None

                if len(defs) > 1:
                    raise CC.ArtifactException("More than one {filetype} External Links were found for {device}: {urls}".format(filetype = filetype, device = self.name(), urls = map(lambda u: u.uri(), defs)), self.name())

                return defs[0].downloadExternalLink(self.defaultFilename(extension), extension, filetype = filetype, git_tag = git_tag)

            # device external links have higher priority than device type external links
            art = __checkExternalLinkList(dev_defs)
            if art is not None:
                return art

            return __checkExternalLinkList(devtype_defs)


        # returns a stable list of controlled devices
        # Returns: []
        def buildControlsList(self, include_self = False, verbose = False):
            self.putInControlledTree()

            # find devices this device _directly_ controls
            pool = self.controls()

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

            if verbose:
                print("\r" + "#" * 60)
                print("Device at root: " + self.name() + "\n")
                print(self.name() + " controls: ")

            # sort items into a list
            def sortkey(device):
                return device.name()
            pool = list()
            for device_type in sorted(controlled_devices):
                if verbose:
                    print("\t- " + device_type)

                for dev in sorted(controlled_devices[device_type], key=sortkey):
                    pool.append(dev)
                    dev.putInControlledTree()
                    if verbose:
                        print("\t\t-- " + dev.name())

            if verbose:
                print("\n")

            if include_self:
                pool.insert(0, self)

            return pool


        def toFactory(self, filename, directory = ".", git_tag = None, script = None):
            return self.ccdb.toFactory(filename, directory, git_tag = git_tag, root = self, script = script);



    def __init__(self, clear_templates = True):
        self._clear_templates = clear_templates

        self.__clear()


    @staticmethod
    def addArgs(parser):
        import argparse

        ccdb_args = parser.add_argument_group("CCDB related options")

        ccdb_flavors = ccdb_args.add_mutually_exclusive_group()
        ccdb_flavors.add_argument(
                                  '--ccdb-test',
                                  dest     = "ccdb_test",
                                  help     = 'select CCDB test database',
                                  action   = 'store_true',
                                  required = False)

        ccdb_flavors.add_argument(
                                  '--ccdb-devel',
                                  dest     = "ccdb_devel",
                                  help     = argparse.SUPPRESS, #selects CCDB development database
                                  action   = 'store_true',
                                  required = False)

        # this argument is just for show as the corresponding value is
        # set to True by default
        ccdb_flavors.add_argument(
                                  '--ccdb-production',
                                  dest     = "ccdb_production",
                                  help     = 'select production CCDB database',
                                  action   = 'store_true',
                                  required = False)

        ccdb_flavors.add_argument(
                                  '--ccdb',
                                  dest     = "ccdb",
                                  help     = 'use a CCDB dump as backend',
                                  metavar  = 'directory-to-CCDB-dump / name-of-.ccdb.zip',
                                  type     = str,
                                  required = False)

        ccdb_args.add_argument(
                               '--cached',
                               dest     = "clear_ccdb_cache",
                               help     = 'do not clear "templates" folder; use the templates downloaded by a previous run',
                               # be aware of the inverse logic between the meaning of the option and the meaning of the variable
                               default  = True,
                               action   = 'store_false')

        return parser


    @staticmethod
    def urlComps(url):
        url_comps = urlsplit(url)

        comps = url_comps.netloc + url_comps.path
        return comps.split('/')


    @staticmethod
    def urlToFilename(url):
        comps = CC.urlComps(url)
        # assume the last component is a filename
        return comps[-1]


    @staticmethod
    def urlToDir(url):
        comps = CC.urlComps(url)

        # ignore the last component, it is assumed to be a filename
        del comps[-1]

        return os_path.join(*map(lambda sde: helpers.sanitizeFilename(sde), comps))


    @staticmethod
    def saveas(uniqueID, filename, directory, CreateDir = True):
        try:
            return CC.paths_cached[uniqueID, filename, directory]
        except KeyError:
            dtdir = os_path.join(directory, helpers.sanitizeFilename(uniqueID))
            if CreateDir:
                helpers.makedirs(dtdir)
            path = os_path.normpath(os_path.join(dtdir, helpers.sanitizeFilename(filename)))
            CC.paths_cached[uniqueID, filename, directory] = path
            return path


    @staticmethod
    def tostring(string):
        if isinstance(string, str) or string is None:
            return string

        if isinstance(string, list):
            return [CC.tostring(s) for s in string]

        if isinstance(string, dict):
            newdict = dict()
            for k in string:
                newdict[CC.tostring(k)] = CC.tostring(string[k])

            return newdict

        if isinstance(string, int):
            return str(string)

        try:
            # Have to check for unicode type in Python2
            # isinstance(string, str) above is enough in Python3
            if not isinstance(string, unicode):
                raise CC.Exception("Unhandled type", type(string), string)
        except NameError:
            # Sadly, the 'from None' part is not valid in Python2
            raise CC.Exception("Unhandled type", type(string), string)# from None

        try:
            return string.encode("unicode-escape").decode("string-escape").decode("utf-8").encode("utf-8")
        except UnicodeDecodeError as e:
            return string.encode("utf-8")


    @staticmethod
    def get(url, **keyword_params):
        netloc = urlsplit(url).netloc

        try:
            session = CC.sessions_cached[netloc]
        except KeyError:
            session = requests.session()
            CC.sessions_cached[netloc] = session

        return session.get(url, **keyword_params)


    @staticmethod
    def download(url, save_as, verify_ssl_cert = True):
        result = CC.get(url, verify = verify_ssl_cert)

        if result.status_code != 200:
            raise CC.DownloadException(url = url, code = result.status_code)

        # 'w' overwrites the file if it exists
        with open(save_as, 'wb') as f:
            for line in result:
                f.write(line)

        return save_as


    def __clear(self):
        # all devices; key, Device pairs
        self._devices              = dict()

        self._hashSum              = None

        # cache for device, property dictionary
        self._propDict             = dict()

        # cache for ^() expressions
        # key: (device, expression), value: property
        self._backtrackCache       = dict()

        # cache of downloaded artifacts
        CC.Artifact.downloadedArtifacts = list()

        if self._clear_templates:
            # clear templates downloaded in a previous run
            helpers.rmdirs(CC.TEMPLATE_DIR)
            CC.paths_cached = dict()
        else:
            print("Reusing templates of any previous run")

        helpers.makedirs(CC.TEMPLATE_DIR)


    # clear whatever we have. let other implementations override
    def clear(self):
        self.__clear()


    # Returns: CC.Device
    def device(self, deviceName, cachedOnly = False):
        try:
            return self._devices[self.deviceName(deviceName)]
        except KeyError:
            if cachedOnly:
                return None

            device      = self._device(deviceName)
            device.ccdb = self

            return device


    # Returns: the device name
    # CCDB returns a dictionary of {nameId, Id, name} in controls/controlledBy/etc list
    def deviceName(self, deviceName):
        return deviceName


    # Returns: {}
    def _propertiesDict(self, device, prefixToIgnore = "PLCF#"):
        if prefixToIgnore == True:
            prefixToIgnore = "PLCF#"

        if prefixToIgnore == "":
            return device.properties()

        deviceName = device.name()

        if (deviceName, prefixToIgnore) in self._propDict:
            return self._propDict[deviceName, prefixToIgnore]

        result = {}
        for (name, value) in device.properties().iteritems():
            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            result[name] = value

        self._propDict[deviceName, prefixToIgnore] = result

        return result


    # Returns: []
    def getSimilarDevices(self, deviceName):
        assert isinstance(deviceName, str)

        raise NotImplementedError


    def toFactory(self, filename, directory = ".", git_tag = None, script = None, root = None):
        devtypes      = []
        fact_devtypes = []
        fact_root     = []
        fact_devs     = []

        setProperty_str = """{var}.setProperty("{k}", "{v}")"""

        def setProperty(out, dev, var):
            comment = False
            for (k, v) in dev.properties().items():
                if not comment:
                    comment = True
                    out.append("# Properties")
                out.append(setProperty_str.format(var = var,
                                                  k    = k,
                                                  v    = v))

        def addDevice(dev, fact, var, output):
            devType = dev.deviceType()
            if devType == "PLC":
                output.append("""#
# Adding PLC: {device}
#
{var} = {fact}.addPLC("{device}")""".format(var = var, fact = fact, device = dev.name()))
            elif devType == "PLC_BECKHOFF":
                output.append("""#
# Adding Beckhoff PLC: {device}
#
{var} = {fact}.addBECKHOFF("{device}")""".format(var = var, fact = fact, device = dev.name()))
            else:
                output.append("""#
# Adding device {device} of type {type}
#
{var} = {fact}.addDevice("{type}", "{device}")""".format(var = var, fact = fact, type = devType, device = dev.name()))

            setProperty(output, dev, var)

            comment = False
            for elink in dev.externalLinks():
                if not elink.is_perdevtype():
                    if not comment:
                        comment = True
                        output.append("# External links")
                    output.append("""{var}.addLink("{name}", "{link}")""".format(var     = var,
                                                                                 name    = elink.name(),
                                                                                 link    = elink.uri()))

            comment = False
            for art in dev.artifacts():
                if not art.is_perdevtype() and art.is_file():
                    if not comment:
                        comment = True
                        output.append("# Artifacts")
                    output.append("""{var}.addArtifact("{name}")""".format(var  = var,
                                                                           name = art.name()))

            output.append('')

        def ctrls(device, var, idx = None):
            cvar = "{}{}".format(var, idx) if idx else "dev"
            idx  = idx + 1 if idx else 1
            for dev in device.controls():
                addDevice(dev, var, cvar, fact_devs)
                ctrls(dev, cvar, idx)

        # Define device type external links
        plc = None
        for devname in sorted(self._devices.keys()):
            dev      = self.device(devname)
            devType  = dev.deviceType()
            exLinks  = sorted(dev.externalLinks(), key = lambda x: x.name())

            if devType not in devtypes:
                if root is None and (devType == "PLC" or devType == "PLC_BECKHOFF"):
                    if plc:
                        raise CC.Exception("Cannot determine root device")
                    plc = dev

                devtypes.append(devType)

                newline = False
                comment = False
                for elink in exLinks:
                    if elink.is_perdevtype():
                        if not comment:
                            comment = True
                            fact_devtypes.append("""# External links for {}""".format(devType))
                        fact_devtypes.append("""factory.addLink("{devtype}", "{name}", "{link}")""".format(devtype = devType,
                                                                                                           name    = elink.name(),
                                                                                                           link    = elink.uri()))

                newline = comment
                comment = False
                for art in dev.artifacts():
                    if art.is_perdevtype() and art.is_file():
                        if not comment:
                            comment = True
                            fact_devtypes.append("# Artifacts for {}".format(devType))
                        fact_devtypes.append("""factory.addArtifact("{devtype}", "{name}")""".format(devtype = devType,
                                                                                                     name    = art.name()))

                if newline or comment:
                    fact_devtypes.append('')

        if root is None:
            root = plc

        if root is None:
            raise CC.Exception("Cannot determine root device")

        rootType = root.deviceType()
        if rootType == "IOC":
            root_var = "ioc"
        elif rootType == "PLC" or rootType == "PLC_BECKHOFF":
            root_var = "plc"
        else:
            root_var = "root"

        addDevice(root, "factory", root_var, fact_root)
        ctrls(root, root_var)

        fact = """#!/usr/bin/env python2

import os
import sys

sys.path.append(os.path.curdir)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ccdb_factory import CCDB_Factory

factory = CCDB_Factory({factory_options})

{links}
{root}
{devs}

#
# Saving the created CCDB
#
factory.save("{filename}")""".format(factory_options = 'git_tag = "{}"'.format(git_tag) if git_tag is not None else "",
                                     links           = "\n".join(fact_devtypes),
                                     root            = "\n".join(fact_root),
                                     devs            = "\n".join(fact_devs),
                                     filename        = filename)

        if script is None:
            script = filename

        if not script.endswith("_ccdb.py"):
            script += "_ccdb.py"

        script = os_path.join(directory, helpers.sanitizeFilename(script))
        with open(script, "w") as f:
            print(fact, file = f)

        return script


    def dump(self, filename, directory = "."):
        return self.save(filename, directory)


    def save(self, filename, directory = "."):
        assert isinstance(filename, str)

        import zipfile
        if not filename.endswith(".ccdb.zip"):
            filename += ".ccdb.zip"

        filename = os_path.join(directory, helpers.sanitizeFilename(filename))
        dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)

        dumpfile.writestr(os_path.join("ccdb", "device.dict"), str(self._devices))
        for template in self.Artifact.downloadedArtifacts:
            dumpfile.write(template, os_path.join("ccdb", template))

        return filename


    @staticmethod
    def load(filename):
        from ccdb_dump import CCDB_Dump
        print("Trying to load CC dump from", filename)
        return CCDB_Dump.load(filename)


    def _backtrack(self, device, prop):
        assert isinstance(prop,   str)

        deviceName = device.name()

        # starting by one device, looking for property X, find a device
        # in a higher level of the hierarchy that has that property

        if (deviceName, prop) in self._backtrackCache:
            return self._backtrackCache[deviceName, prop]

        # starting point: all devices 'device' is controlled by
        leftToProcess = device.controlledBy(True)
        # if not controlled by anything, search device itself. Mandatory for artifacts attached to the root device itself
        if not leftToProcess:
            leftToProcess = [ device ]

        # keep track of number of iterations
        count = 0

        # process tree in BFS manner
        processed = []
        while True:

            if count > 200:
                raise CC.Exception("Something went wrong; too many iterations in backtracking while searching for property " + prop)

            if len(leftToProcess) == 0:
                print("error in  backtracking after {} iterations; probably invalid input while searching for property {}".format(count, prop))
                return " ==== BACKTRACKING ERROR ==== "

            elem = leftToProcess.pop()

            if elem in processed:
                continue

            processed.append(elem)

            # get properties of device
            propDict = elem.propertiesDict()

            if prop in propDict:
                val = propDict.get(prop)
                self._backtrackCache[deviceName, prop] = val

                return val

            # desired property not found in device x
            else:
                c = elem.controlledBy(True)
                if c is not None:
                  leftToProcess = c + leftToProcess
                  count        += 1


    def computeHash(self, hashobj):
        # compute checksum and hash
        # from all keys and their corresponding values in order, e.g.
        # key_1, value_1, key_2, value_2, ... key_n, value_n

        # get all devices
        deviceNames = self._devices.keys()

        # now the same for each device in alphabetical order:
        for deviceName in sorted(deviceNames):
            device = self._devices[deviceName]

            # Make sure that only controlled devices are hashed
            if not device.isInControlledTree():
                continue

            hashobj.update(deviceName)

            for k in sorted(device.keys()):
                tmp = self._getOrderedString([device[k]])

                hashobj.update(k)
                hashobj.update(tmp)


    # recursively process input in order to create an "ordered"
    # string of all properties
    @staticmethod
    def _getOrderedString(inp):
        assert isinstance(inp, list)

        res       = ""
        toProcess = list(inp)

        while not toProcess == []:

            head = toProcess.pop(0)

            if isinstance(head, str):
                res += head

            elif isinstance(head, list):
                for elem in head:
                    toProcess.append(elem)

            elif isinstance(head, dict):
                for elem in sorted(head.keys()):
                    toProcess.append(elem)
                    toProcess.append(head[elem])

            elif isinstance(head, bool):
                res += str(head)

            elif head is None:
                continue

            else:
                # Python3 does not have basestring
                try:
                    if isinstance(head, basestring):
                        res += head
                        continue
                except:
                    pass
                raise CC.Exception("Input error", type(head))

        return res
