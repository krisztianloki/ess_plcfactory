from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Controls & Configuration abstraction """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


# Python libraries
from os import path as os_path
import getpass

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
import levenshtein
import plcf_git as git



class CC(object):
    TEMPLATE_DIR    = "templates"
    TAG_SEPARATOR   = "__"
    GIT_SUFFIX      = ".git"
    CCDB_ZIP_SUFFIX = ".ccdb.zip"
    DEVICE_DICT     = "device.dict"
    paths_cached    = dict()
    sessions_cached = dict()
    repos_cached    = dict()


    class Exception(Exception):
        """Base class for Controls and Configuration exceptions"""
        def __str__(self):
            if self.message:
                return """
{banner}
{msg}
{banner}
""".format(banner = "*" * max(map(lambda x: len(x), self.message.splitlines())), msg = self.message)
            else:
                return super(CC.Exception, self).__str__()



    class DownloadException(Exception):
        def __init__(self, url, code):
            super(CC.DownloadException, self).__init__()
            self.url  = url
            self.code = code
            if url is not None:
                self.message = "Cannot download {url}: error {code}".format(url = self.url, code = self.code)



    class ArtifactException(DownloadException):
        def __init__(self, dloadexception, deviceName = None, filename = None):
            self.deviceName = deviceName
            self.filename   = filename

            if isinstance(dloadexception, CC.DownloadException):
                super(CC.ArtifactException, self).__init__(url = dloadexception.url, code = dloadexception.code)
                self.message = "Cannot get artifact {art} of {device}: error {code} ({url})".format(device = self.deviceName,
                                                                                                    art    = self.filename,
                                                                                                    code   = self.code,
                                                                                                    url    = self.url)
            else:
                super(CC.ArtifactException, self).__init__(None, None)
                self.message = dloadexception



    class NoSuchDeviceException(Exception):
        pass



    class BasicAuth(requests.auth.AuthBase):
        def __init__(self, username = None):
            super(CC.BasicAuth, self).__init__()

            if username is None:
                username = getpass.getuser()
            self.username = username
            self.password = None


        def __eq__(self, other):
            return all([
                        self.username == getattr(other, 'username', None),
                        self.password == getattr(other, 'password', None)
                       ])


        def __ne__(self, other):
            return not self == other


        def __call__(self, r):
            if not self.password:
                self.password = getpass.getpass("Password of {} for {}: ".format(self.username, r.url.split('?')[0]))
            r.headers['Authorization'] = requests.auth._basic_auth_str(self.username, self.password)
            return r


        def isvalid(self):
            return self.password is not None



    class Artifact(object):
        # list of the path names of downloaded artifacts
        # FIXME: should make this per-CC
        downloadedArtifacts = list()

        def __init__(self, device):
            super(CC.Artifact, self).__init__()

            self._device = device

            self._saveas         = None
            self._saveasurl      = None
            self._saveasversion  = None
            self._saveasfilename = None


        def __repr__(self):
            return self.name()


        def name(self):
            raise NotImplementedError


        def is_file(self):
            raise NotImplementedError


        def is_uri(self):
            raise NotImplementedError


        def is_git(self):
            return self.is_uri() and self.uri().endswith(CC.GIT_SUFFIX)


        def is_perdevtype(self):
            raise NotImplementedError


        def filename(self):
            raise NotImplementedError


        def uri(self):
            raise NotImplementedError


        def uniqueID(self):
            raise NotImplementedError


        def saveas(self):
            """
            Returns the full path (relative to the current directory) of the downloaded artifact filename
            """
            if self._saveas is None:
                if not self.is_file():
                    raise NotImplementedError
                self._saveas = CC.saveas(self.uniqueID(), self.saveas_filename(), self._device.ccdb.TEMPLATE_DIR)

            return self._saveas


        def saveas_url(self):
            """
            Returns the full url from where the artifact has to be downloaded
            """
            if self._saveasurl is None:
                raise NotImplementedError

            return self._saveasurl


        def saveas_version(self):
            """
            Returns the version that needs to be downloaded (the branch/tag if git repo)
            """
            if self._saveasversion is None:
                raise NotImplementedError

            return self._saveasversion


        def saveas_filename(self):
            if self._saveasfilename is None:
                if not self.is_file():
                    raise NotImplementedError
                self._saveasfilename = self.filename()

            return self._saveasfilename


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

                # Check if the specified filename is valid
                if filename != helpers.sanitize_path(filename):
                    raise CC.ArtifactException("Invalid filename in External Link for {device}: {name}".format(device = self._device.name(), name = filename), self._device.name(), filename)
            else:
                base = linkfile

            if git_tag is None:
                git_tag = self._device.properties().get(base + " VERSION", "master")

            print("Downloading {filetype} file {filename} (version {version}) from {url}".format(filetype = filetype,
                                                                                                 filename = filename,
                                                                                                 url      = self.uri(),
                                                                                                 version  = git_tag))

            self._saveasversion  = git_tag
            self._saveasfilename = filename

            return self.download()


        def prepare_to_download(self):
            if self.is_uri():
                git_tag  = self.saveas_version()
                filename = self.saveas_filename()
                # NOTE: we _must not_ use CC.TEMPLATE_DIR here,
                # CCDB_Dump relies on creating an instance variant of TEMPLATE_DIR to point it to its own templates directory
                if not self.is_git():
                    url = CC.urljoin(self.uri(), "raw", git_tag)
                    self._saveasurl      = CC.urljoin(url, filename)
                    self._saveas         = CC.saveas(self.uniqueID(), filename, os_path.join(self._device.ccdb.TEMPLATE_DIR, CC.url_to_path(url)))
                else:
                    # Make sure that only one version is requested of the same repo
                    # This is a limitation of the current implementation
                    if CC.repos_cached.get(self.uri(), git_tag) != git_tag:
                        raise CC.ArtifactException("Cannot mix different versions/branches of the same repository: {}".format(self.uri()))

                    self._saveasurl      = self.uri()
                    # We could remove the '.git' extension from the url but I see no point in doing that
                    self._saveas         = CC.saveas(self.uniqueID(), filename, os_path.join(self._device.ccdb.TEMPLATE_DIR, CC.url_to_path(self.uri())))


        # Returns: "", the downloaded filename
        def download(self):
            self.prepare_to_download()
            save_as  = self.saveas()

            # check if filename has already been downloaded
            if os_path.exists(save_as):
                return CC.DownloadedArtifact(self)

            try:
                self._download(save_as)
            except CC.DownloadException as e:
                raise CC.ArtifactException(e, deviceName = self._device.name(), filename = self.saveas_filename())

            CC.Artifact.downloadedArtifacts.append(save_as)

            return CC.DownloadedArtifact(self)



    class DownloadedArtifact(object):
        def __init__(self, artifact):
            super(CC.DownloadedArtifact, self).__init__()

            self._epi            = None if artifact.is_file() else artifact.name()
            self._epi_url        = None if artifact.is_file() else artifact.uri()
            self._epi_version    = None if artifact.is_file() else artifact._saveasversion
            self._filename       = artifact.saveas_filename()
            self._url            = artifact.saveas_url()
            self._saved_as       = artifact.saveas()
            self._perdevtype     = artifact.is_perdevtype()


        def saved_as(self):
            return self._saved_as


        def filename(self):
            return self._filename


        def url(self):
            return self._url


        def epi(self):
            return self._epi


        def epi_url(self):
            return self._epi_url


        def epi_version(self):
            return self._epi_version


        def is_perdevtype(self):
            return self._perdevtype



    class DeviceType(object):
        ccdb = None

        def __init__(self, ccdb):
            super(CC.DeviceType, self).__init__()

            if ccdb is not None:
                self.ccdb = ccdb


        def name(self):
            raise NotImplementedError


        def url(self):
            return None



    class Device(object):
        ccdb = None

        def __init__(self, ccdb):
            super(CC.Device, self).__init__()

            self._inControlledTree = False
            if ccdb is not None:
                self.ccdb = ccdb


        def url(self):
            return None


        @staticmethod
        def _ensure(var, default, convert_to_default = True):
            #
            # Do not return None
            #
            if var is not None:
                if isinstance(var, default) or not convert_to_default:
                    return var
                return default(var)

            return default()


        # Returns: {}
        def keys(self):
            raise NotImplementedError


        # Returns: ""
        def name(self):
            raise NotImplementedError


        # Returns: DeviceType
        def type(self):
            raise NotImplementedError


        def putInControlledTree(self):
            self._inControlledTree = True


        def isInControlledTree(self):
            return self._inControlledTree


        # Returns: []
        def controls(self, convert = True):
            return self._ensure(self._controls(), list, convert)


        # Returns: []
        def controlledBy(self, filter_by_controlled_tree = False, convert = True):
            ctrldBy = self._controlledBy(filter_by_controlled_tree)
            if not filter_by_controlled_tree:
                return self._ensure(ctrldBy, list, convert)
            return self._ensure(filter(lambda d: d.isInControlledTree(), ctrldBy), list, convert)


        # Returns: {}
        def properties(self, convert = True):
            return self._ensure(self._properties(), dict, convert)


        # Returns: {}
        def propertiesDict(self, prefixToIgnore = True):
            return self._ensure(self._propertiesDict(), dict)


        # Returns: ""
        def deviceType(self):
            return self._ensure(self._deviceType(), str)


        # Returns: ""
        def description(self):
            return self._ensure(self._description(), str)


        # Returns: []
        def artifacts(self, convert = True):
            return self._ensure(self._artifacts(), list, convert)


        # Returns: []
        def artifactNames(self, convert = True):
            return self._ensure(map(lambda an: an.name(), filter(lambda fa: fa.is_file(), self.artifacts(convert = False))), list, convert)


        # Returns: []
        def externalLinks(self, convert = True):
            return self._ensure(filter(lambda u: u.is_uri(), self.artifacts(convert = False)), list, convert)


        # Returns: ""
        def backtrack(self, prop):
            return self._ensure(self._backtrack(prop), str)


        def defaultFilename(self, extension):
            if extension is None:
                extension = ""
            elif not extension.startswith('.'):
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
        def downloadArtifact(self, extension, device_tag = None, filetype = '', custom_filter = None, filter_args = ()):
            if custom_filter is None:
                def filter_device_tags(artifact):
                    return CC.TAG_SEPARATOR not in artifact.filename()

                def no_filter(artifact):
                    return True

                if not extension.startswith('.'):
                    extension = '.{}'.format(extension)

                if device_tag:
                    # whatever__devicetag.extension
                    suffix = "".join([ CC.TAG_SEPARATOR, device_tag, extension ])
                    custom_filter = no_filter
                else:
                    suffix = extension
                    custom_filter = filter_device_tags

                defs = filter(lambda a: a.is_file() and a.filename().endswith(suffix) and custom_filter(a), self.artifacts())
            else:
                defs = filter(lambda a: a.is_file() and custom_filter(a, *filter_args), self.artifacts())

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
                    raise CC.ArtifactException("More than one {filetype} External Links were found for {device}: {urls}".format(filetype = filetype, device = self.name(), urls = list(map(lambda u: u.uri(), defs))), self.name())

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
                if verbose is True:
                    print("\r" + "#" * 60)
                    print("Device at root: " + self.name() + "\n")
                    print(self.name() + " controls: ")
                else:
                    verbose(self, 'root')

            # sort items into a list
            def sortkey(device):
                return device.name()
            pool = list()
            for device_type in sorted(controlled_devices):
                if verbose:
                    if verbose is True:
                        print("\t- " + device_type)
                    else:
                        verbose(controlled_devices[device_type][0].type(), 'device_type')

                for dev in sorted(controlled_devices[device_type], key=sortkey):
                    pool.append(dev)
                    dev.putInControlledTree()
                    if verbose:
                        if verbose is True:
                            print("\t\t-- " + dev.name())
                        else:
                            verbose(dev, 'device')

            if verbose is True:
                print("\n")

            if include_self:
                pool.insert(0, self)

            return pool


        def toFactory(self, filename, directory = ".", git_tag = None, script = None):
            return self.ccdb.toFactory(filename, directory, git_tag = git_tag, root = self, script = script)



    def __init__(self, clear_templates = True):
        super(CC, self).__init__()

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
                                  help     = argparse.SUPPRESS,  # selects CCDB development database
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
                                  help     = 'use a CCDB dump or custom URL as backend',
                                  metavar  = 'directory-to-CCDB-dump / name-of-.ccdb.zip / URL to CCDB REST interface',
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
    def urlsplit(url):
        return helpers.urlsplit(url)


    @staticmethod
    def urlquote(string):
        return helpers.urlquote(string)


    @staticmethod
    def url_to_path(url):
        return helpers.url_to_path(url)


    @staticmethod
    def urljoin(base, path, *more):
        return helpers.urljoin(base, path, *more)


    @staticmethod
    def saveas(uniqueID, filename, directory, CreateDir = True):
        try:
            return CC.paths_cached[uniqueID, filename, directory]
        except KeyError:
            dtdir = os_path.join(directory, helpers.sanitize_path(uniqueID))
            if CreateDir:
                helpers.makedirs(dtdir)
            path = os_path.normpath(os_path.join(dtdir, helpers.sanitize_path(filename)))
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
                raise CC.Exception("Unhandled type {}: {}".format(type(string), string))
        except NameError:
            # Sadly, the 'from None' part is not valid in Python2
            raise CC.Exception("Unhandled type {}: {}".format(type(string), string))  # from None

        try:
            return string.encode("unicode-escape").decode("string-escape").decode("utf-8").encode("utf-8")
        except UnicodeDecodeError:
            return string.encode("utf-8")


    @staticmethod
    def get(url, auth = None, **keyword_params):
        netloc = CC.urlsplit(url).netloc

        try:
            (session, auth) = CC.sessions_cached[netloc]
        except KeyError:
            session = requests.session()
            if auth is None:
                auth    = CC.BasicAuth()
            CC.sessions_cached[netloc] = (session, auth)

        # Try without authentication first; don't want to bother users with asking for their password when not really needed
        result = session.get(url, auth = auth if auth.isvalid() else None, **keyword_params)
        if result.status_code == 401:
            result = session.get(url, auth = auth, **keyword_params)

        return result


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


    @staticmethod
    def git_download(url, cwd, version = "master"):
        print("Cloning {}...".format(url))
        git.clone(url, cwd, branch = version)
        git.checkout(cwd, version)
        CC.repos_cached[url] = version


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


    def url(self):
        return None


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
        # Not using 'if prefixToIgnore:' because we really want to check if it is a boolean and true
        if prefixToIgnore is True:
            prefixToIgnore = "PLCF#"

        if prefixToIgnore == "":
            return device.properties()

        deviceName = device.name()

        if (deviceName, prefixToIgnore) in self._propDict:
            return self._propDict[deviceName, prefixToIgnore]

        result = {}
        for (name, value) in device.properties().items():
            # remove prefix if it exists
            if name.startswith(prefixToIgnore):
                name = name[len(prefixToIgnore):]

            result[name] = value

        self._propDict[deviceName, prefixToIgnore] = result

        return result


    # Returns: []
    def getAllDeviceNames(self):
        raise NotImplementedError


    # Returns: []
    def getSimilarDeviceNames(self, deviceName, X = 10):
        """
            Returns the topX most similar device names in the database

            Returns a tuple (filtered, topX):
             - filtered; boolean if the list is filtred to the same System-Subsystem as deviceName
             - topX; a list of device names
        """
        allDevices = self.getAllDeviceNames()

        # keep only device
        slot = deviceName.split(":")
        candidates = None
        if len(slot) > 1:
            slot       = slot[0].lower()
            candidates = filter(lambda x: x.lower().startswith(slot), allDevices)
            filtered   = True

        if not candidates:
            candidates = allDevices
            filtered   = False

        # compute Levenshtein distances
        if candidates:
            candidates = list(map(lambda f: f[1], sorted(map(lambda x: (levenshtein.distance(deviceName, x), x), candidates))[:X]))

        return (filtered, candidates)


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

        script = os_path.join(directory, helpers.sanitize_path(script))
        with open(script, "w") as f:
            print(fact, file = f)

        return script


    def dump(self, filename, directory = "."):
        return self.save(filename, directory)


    def save(self, filename, directory = "."):
        import zipfile
        if isinstance(filename, str):
            if not filename.endswith(CC.CCDB_ZIP_SUFFIX):
                filename += CC.CCDB_ZIP_SUFFIX

            filename = os_path.join(directory, helpers.sanitize_path(filename))
            dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
        else:
            dumpfile = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
            filename = filename.name

        dumpfile.writestr(os_path.join("ccdb", CC.DEVICE_DICT), str(self._devices))
        for template in self.Artifact.downloadedArtifacts:
            dumpfile.write(template, os_path.join("ccdb", template))

        return filename


    @staticmethod
    def open(name = None, **kwargs):
        if name is not None:
            if os_path.exists(name):
                return CC.load(name)
            elif name.endswith(CC.CCDB_ZIP_SUFFIX):
                raise CC.Exception("Cannot find " + name)

        from ccdb import CCDB
        return CCDB(name, **kwargs)


    @staticmethod
    def load(filename):
        from ccdb_dump import CCDB_Dump
        print("Trying to load CC dump from", filename)
        return CCDB_Dump.load(filename)


    def _backtrack(self, device, prop):
        assert isinstance(prop, str)

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
                raise CC.Exception("Input error {}".format(type(head)))

        return res
