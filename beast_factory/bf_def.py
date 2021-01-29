from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

""" BEAST Factory: Alarm Definition Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019, European Spallation Source, Lund"
__license__    = "GPLv3"


from collections import OrderedDict
import codecs
import sys
import datetime

try:
    import helpers
except ImportError:
    import os
    sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.path.pardir))
    import helpers
    del os



def xml_descape(string):
    return string.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")



class BEASTDefException(Exception):
    status = 1
    args_format = """
{}
"""

    def __init__(self, typemsg, *args, **keyword_params):
        self.typemsg        = typemsg
        self.args           = args
        if isinstance(args[0], Exception):
            try:
                keyword_params.update(args[0].keyword_params)
            except:
                pass
        self.keyword_params = keyword_params


    def __call__(self, *args):
        return self.__class__(self.typemsg, *(self.args + args))


    def __repr__(self):
        try:
            return """{error} at line {linenum}: {line}{args}""".format(error   = self.typemsg,
                                                                        linenum = self.keyword_params["linenum"],
                                                                        line    = self.keyword_params.get("line", '<N/A>'),
                                                                        args    = self.args_format.format(self.args[0]) if self.args[0] else "")
        except KeyError:
            return """{error}: {args}""".format(error   = self.typemsg,
                                                args    = self.args_format.format(self.args[0]) if self.args[0] else "")


    def __str__(self):
        return repr(self)


    def type(self):
        return self.typemsg


    def add_params(self, **keyword_params):
        self.keyword_params.update(keyword_params)



class BEASTDefSyntaxError(BEASTDefException):
    def __init__(self, *args, **keyword_params):
        super(BEASTDefSyntaxError, self).__init__("Syntax error", *args, **keyword_params)



class BEASTDefInternalError(BEASTDefException):
    def __init__(self, *args, **keyword_params):
        super(BEASTDefInternalError, self).__init__("Internal error", *args, **keyword_params)



class BEASTDefPrematureEnd(BEASTDefSyntaxError):
    def __init__(self, *args):
        super(BEASTDefPrematureEnd, self).__init__("Unexpected EOF while parsing", *args)



class BEASTDefFeatureMissingError(BEASTDefSyntaxError):
    def __init__(self, feature):
        super(BEASTDefFeatureMissingError, self).__init__("Required feature '{}' is not supported in this version".format(feature))



def beastdef_assert_instance(inst_cond, var, type):
    if not inst_cond:
        raise BEASTDefInternalError("'{param}' must be of type {type}!".format(param = var, type = str(type)))



class BEAST_BASE(object):
    def __init__(self, line, comment = False):
        if isinstance(line, tuple):
            line, lineno = line
        else:
            lineno = -1

        beastdef_assert_instance(isinstance(line,    str) or isinstance(line, unicode), "line", str)
        beastdef_assert_instance(isinstance(lineno,  int), "lineno", int)
        beastdef_assert_instance(isinstance(comment, bool), "comment", bool)

        self._line     = line.lstrip()
        self._lineno   = lineno
        self._comment  = comment
        self._warnings = None


    def is_comment(self):
        return self._comment


    def line(self):
        return self._line


    def lineno(self):
        return self._lineno


    def warnings(self):
        return self._warnings


    def _add_warning(self, warn):
        if self._warnings is None:
            self._warnings = [ "At line number {lnum}:".format(lnum = self.lineno()), warn ]
        else:
            self._warnings.append(warn)

        return warn



#
# Guidance, Display, Command, Automated action
#
class BEAST_GDCA(BEAST_BASE):
    def __init__(self, line):
        super(BEAST_GDCA, self).__init__(line)

        self._guidances         = []
        self._displays          = []
        self._commands          = []
        self._automated_actions = []


    def add_guidance(self, guidance):
        self._guidances.append(guidance)


    def add_display(self, display):
        self._displays.append(display)


    def add_command(self, command):
        self._commands.append(command)


    def add_automated_action(self, automated_action):
        self._automated_actions.append(automated_action)


    @staticmethod
    def __xmllist(element, ls, etree):
        for guidance in ls:
            guidance.toxml(element, etree)


    def toxml(self, element, etree):
        self.__xmllist(element, self._guidances, etree)
        self.__xmllist(element, self._commands, etree)
        self.__xmllist(element, self._displays, etree)
        self.__xmllist(element, self._automated_actions, etree)

        return element



class BEAST_COMPONENT(BEAST_GDCA):
    def __init__(self, line, name, path):
        super(BEAST_COMPONENT, self).__init__(line)

        self._name     = name
        self._path     = list(path)
        self._children = OrderedDict()
        self._pvs      = OrderedDict()


    def __repr__(self):
        return self._name


    def __str__(self):
        return self._name


    def name(self):
        return self._name


    def components(self):
        return self._children


    def pvs(self):
        return self._pvs.values()


    def path(self):
        return self._path


    def strpath(self, include_self = False):
        p = ['']
        p.extend([c.name() for c in self._path])
        if include_self:
            p.append(self._name)

        try:
            p[1]
        except IndexError:
            return "/"

        return "/".join(p)


    def xpath(self):
        return "{}/component[@name='{}']".format("".join(["/component[@name='{}']".format(i.name()) for i in self._path]), self._name)


    def add_component(self, child):
        beastdef_assert_instance(isinstance(child, BEAST_COMPONENT), "child", BEAST_COMPONENT)

        try:
            if self._children[child.name()] != child:
                raise BEASTDefSyntaxError("Component ('{}') is already defined at this level: '{}'".format(child.name(), self.strpath(True)))
        except KeyError:
            pass

        self._children[child.name()] = child


    def add_pv(self, pv):
        beastdef_assert_instance(isinstance(pv, BEAST_PV), "child", BEAST_PV)

        if pv.name() in self._pvs:
            raise BEASTDefSyntaxError("PV ('{}') is already defined at this level: '{}'".format(pv.name(), self.strpath(True)))

        self._pvs[pv.name()] = pv


    def toxml(self, parent, etree):
        element = etree.SubElement(parent, "component", name = self._name)

        super(BEAST_COMPONENT, self).toxml(element, etree)

        for pv in self.pvs():
            pv.toxml(element, etree)

        for child in self._children.values():
            child.toxml(element, etree)

        return element



class BEAST_PV(BEAST_GDCA):
    def __init__(self, line, name, delay, count, defaults):
        super(BEAST_PV, self).__init__(line)

        self._name     = name
        self._desc     = None
        self._delay    = delay
        self._count    = count

        self._enabled      = defaults['enabled']
        self._latching     = defaults['latching']
        self._annunciating = defaults['annunciating']
        self._filter       = defaults['filter']


    def __repr__(self):
        return self._name


    def toxml(self, parent, etree):
        element = etree.SubElement(parent, "pv", name = self._name)

        if self._desc is not None:
            etree.SubElement(element, "description").text = self._desc

        etree.SubElement(element, "enabled").text      = str(self._enabled).lower()
        etree.SubElement(element, "latching").text     = str(self._latching).lower()
        etree.SubElement(element, "annunciating").text = str(self._annunciating).lower()

        if self._delay:
            etree.SubElement(element, "delay").text = str(self._delay)

        if self._count:
            etree.SubElement(element, "count").text = str(self._count)

        if self._filter:
            etree.SubElement(element, "filter").text = str(self._filter)

        return super(BEAST_PV, self).toxml(element, etree)


    def name(self):
        return self._name


    def description(self):
        return self._desc


    def add_description(self, desc):
        self._desc = desc


    def disable(self, val):
        self._enabled = not val


    def set_latching(self, latching):
        self._latching = latching


    def set_annunciating(self, annunciating):
        self._annunciating = annunciating


    def set_filter(self, expression):
        self._filter = expression



class BEAST_TitleDetailsDelay(BEAST_BASE):
    def __init__(self, line, tag, title, details, delay = None):
        super(BEAST_TitleDetailsDelay, self).__init__(line)

        self._tag     = tag
        self._title   = title
        self._details = xml_descape(details)
        self._delay   = delay


    def toxml(self, parent, etree):
        element = etree.SubElement(parent, self._tag)

        etree.SubElement(element, "title").text     = self._title
        etree.SubElement(element, "details").text   = self._details

        if self._delay is not None:
            etree.SubElement(element, "delay").text = str(self._delay)

        return element



class BEAST_GUIDANCE(BEAST_TitleDetailsDelay):
    def __init__(self, line, title, details):
        super(BEAST_GUIDANCE, self).__init__(line, 'guidance', title, details)



class BEAST_DISPLAY(BEAST_TitleDetailsDelay):
    def __init__(self, line, title, details):
        super(BEAST_DISPLAY, self).__init__(line, 'display', title, details)



class BEAST_COMMAND(BEAST_TitleDetailsDelay):
    def __init__(self, line, title, details):
        super(BEAST_COMMAND, self).__init__(line, 'command', title, details)



class BEAST_AUTOMATED_ACTION(BEAST_TitleDetailsDelay):
    def __init__(self, line, title, details, delay):
        super(BEAST_AUTOMATED_ACTION, self).__init__(line, 'automated_action', title, details, delay)



class BEAST_DEF_INTERFACE_FUNC(object):
    def __init__(self, var):
        self._var = var



def python2_unicodeargs(args):
    return tuple([ i if not isinstance(i, str) else helpers.tounicode(i) for i in args ])


def python3_unicodeargs(args):
    return args


try:
    isinstance('h', unicode)
    unicodeargs = python2_unicodeargs
except NameError:
    unicodeargs = python3_unicodeargs


def alarmtree_interface(func):
    def alarmtree_interface_func(*args, **kwargs):
        kwargs["__ALARM_TREE_FUNC__"] = True
        return func(*args, **kwargs)

    return alarmtree_interface_func


def beastdef_interface(func):
    def beastdef_interface_func(*args, **kwargs):
        if args is not None and isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], BEAST_DEF):
            alarm_tree = kwargs.pop("__ALARM_TREE_FUNC__", False)
            if args[0]._alarm_tree and not alarm_tree:
                raise BEASTDefSyntaxError("Function not valid during alarm tree definition")

            # Convert every str to unicode
            args = unicodeargs(args)
            var = func(*args, **kwargs)

            # If the function is an alias, get the real one
            while isinstance(var, BEAST_DEF_INTERFACE_FUNC):
                var = var._var

            if not isinstance(var, BEAST_BASE):
                raise BEASTDefInternalError("Function '{f}' not returning variable, please file a bug report".format(f = func.__name__))
            return BEAST_DEF_INTERFACE_FUNC(var)
        else:
            raise BEASTDefSyntaxError("Trying to call non-interface function '{f}'".format(f = func.__name__))

    return beastdef_interface_func



class BEAST_DEF(object):
    def __init__(self, merge_with = None):
        if merge_with is not None:
            if not isinstance(merge_with, BEAST_DEF):
                raise BEASTDefInternalError("Cannot merge with non-BEAST_DEF")

            self._root_components = merge_with._root_components
        else:
            # Root components
            self._root_components = OrderedDict()

        # Not defining alarm tree
        self._alarm_tree = False

        # Defined titles to be used in guidance/display/command/automated_action
        # Default and titles defined in the alarm tree
        self._global_titles   = dict()
        self._global_defaults = { 'enabled'      : True,
                                  'latching'     : True,
                                  'annunciating' : False,
                                  'filter'       : None,
                                }

        # Includes
        # Device includes
        self._device_includes = dict()
        # Device type includes
        self._devtype_includes = dict()

        # The config name
        self._config = None

        # Initialize per-device(type) structures
        self._reset()

        self._evalEnv = dict()
        self._evalEnv['__builtins__'] = None
        self._evalEnv['True']         = True
        self._evalEnv['False']        = False

        for f in dir(self):
            val = getattr(self, f)
            if not hasattr(val, '__call__') or f.startswith('_'):
                continue

            if val.__name__ in [ "beastdef_interface_func", "alarmtree_interface_func" ]:
                self._evalEnv[f] = val


    def __len__(self):
        return len(self._root_components)


    def _eval(self, line):
        keyword = line.split('(')[0]
        if keyword not in self._evalEnv:
            raise BEASTDefSyntaxError("Not supported keyword: '{}'".format(keyword))

        try:
            result = eval(line, self._evalEnv)
        except NameError as e:
            raise BEASTDefSyntaxError(e)
        except TypeError as e:
            words = e.args[0].split(' ')
            if len(words) > 1:
                first_word = words[0]
                if first_word[:-2] in self._evalEnv and words[1] == 'takes' and words[2] == 'exactly':
                    # Decrease numbers by 1 ('self' should be hidden from user)
                    words[3] = str(int(words[3]) - 1)
                    words[5] = "({}".format(int(words[5][1:]) - 1)
                    e.args = (" ".join(words),)
                    raise BEASTDefSyntaxError(e)
            raise e

        if not isinstance(result, BEAST_DEF_INTERFACE_FUNC):
           raise BEASTDefSyntaxError("Missing parentheses?")


    def _reset(self):
        # The PV name has to be prefixed
        self._devicename = None

        # Current component and pv
        self._component  = None
        self._pv         = None

        # Path to current component
        self._components = []

        # Not processing on behalf of an include directive
        self._including  = False

        # Initialize titles and defaults to the globally defined ones
        self._titles     = dict(self._global_titles)
        self._defaults   = dict(self._global_defaults)


    def _parse(self, line, linenum):
        self._line = (line, linenum)
        stripped_line = line

        try:
            if not isinstance(line, str) and not isinstance(line, unicode):
                raise BEASTDefSyntaxError("Alarm definition lines must be strings!")

            stripped_line = line.strip()
            if stripped_line.startswith("_"):
                raise BEASTDefSyntaxError("Alarm definition lines cannot start with '_'")

            if stripped_line.startswith("#-"):
                return

            if stripped_line.startswith("#") or stripped_line == "":
                return

            self._eval(stripped_line)
        except BEASTDefException as e:
            e.add_params(line = stripped_line, linenum = linenum)
            raise e
        except AssertionError as e:
            raise BEASTDefInternalError(e, line = stripped_line, linenum = linenum)
        except SyntaxError as e:
            if e.msg == "unexpected EOF while parsing":
                raise BEASTDefPrematureEnd()
            elif e.msg == "EOF while scanning triple-quoted string literal":
                raise BEASTDefPrematureEnd()
            elif e.msg == "invalid syntax" and e.lineno > 1 and len(stripped_line.splitlines()[e.lineno - 1]) == e.offset:
                raise BEASTDefPrematureEnd()
            raise BEASTDefSyntaxError(e.msg, line = stripped_line, linenum = linenum + e.lineno - 1)
        except TypeError as e:
            if "got an unexpected keyword argument" in e.message:
                raise BEASTDefSyntaxError(e.message, line = stripped_line, linenum = linenum)

            raise


    def _read_def(self, def_file):
        with codecs.open(def_file, 'r', encoding = 'utf-8') as defs:
            multiline    = None
            multilinenum = 1
            linenum      = 1

            for line in defs:
                try:
                    if multiline:
                        multiline += line
                        self._parse(multiline, multilinenum)
                        multiline = None
                    else:
                        self._parse(line, linenum)
                except BEASTDefPrematureEnd:
                    if multiline is None:
                        multiline    = line
                        multilinenum = linenum

                linenum += 1

            if multiline:
                raise BEASTDefPrematureEnd(def_file)


    def parse_alarm_tree(self, def_file, config = None):
        self._alarm_tree = True

        self._read_def(def_file)

        # Save defined titles and defaults
        self._global_defaults = self._defaults
        self._global_titles   = self._titles

        if config is not None:
            self._config = config

        if self._config is None:
            raise BEASTDefSyntaxError("No config name is defined in alarm tree and no --config option was specified")

        self._alarm_tree = False

        return self._config


    def parse(self, def_file, device = None):
        self._reset()

        if device is not None:
            devicename = device.name()
            devicetype = device.deviceType()
        else:
            devicename = None
            devicetype = None

        try:
            self._component = self._device_includes[devicename]
            self._including = True
        except KeyError:
            try:
                self._component = self._devtype_includes[devicetype]
                self._including = True
            except KeyError:
                pass

        if def_file.endswith('.alarms-template'):
            if device is None:
                raise BEASTDefSyntaxError(".alarms-template cannot be used in standalone mode")
            self._devicename = devicename
        elif self._including:
            raise BEASTDefSyntaxError("Only .alarms-template definitions can be included")

        self._read_def(def_file)


    def fromxml(self, xml_file, config):
        from .alarm_saxparser import ALARM_SAX_PARSER, AlarmSaxException

        try:
            ALARM_SAX_PARSER.parse(self, xml_file)
        except AlarmSaxException as e:
            raise BEASTDefInternalError(e)

        self._config = config

        return self._config


    def toxml(self, etree, repo, branch, commit):
        xml_tree = etree.ElementTree(etree.Element('config'))
        root     = xml_tree.getroot()

        root.tag = "config"
        root.attrib.clear()
        root.attrib['name'] = self._config

        comment = etree.Comment("""
  Alarm configuration generated by BEASTFactory using the following arguments (please remove the spaces between the hyphens):
  {args}

  Repository: {repo}
  Branch:     {branch}
  Commit:     {commit}
  Date:       {date}
""".format(args   = " ".join([i.replace("--", "- -") for i in sys.argv[1:]]),
           repo   = repo,
           branch = branch,
           commit = commit,
           date   = '{:%Y.%m.%d. %H:%M:%S}'.format(datetime.datetime.now())))

        try:
            root.addprevious(comment)
        except AttributeError:
            # The ElementTree implementation does not have addprevious()
            pass

        for component in self.components().values():
            component.toxml(root, etree = etree)

        return xml_tree


    def components(self):
        return self._root_components


    @alarmtree_interface
    @beastdef_interface
    def config(self, name):
        if not self._alarm_tree:
            raise BEASTDefSyntaxError("Function is only valid during alarm tree definition")

        self._config = name

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def default_latching(self, latch):
        beastdef_assert_instance(isinstance(latch, bool), "latching", bool)

        self._defaults['latching'] = latch

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def default_annunciating(self, annunciate):
        beastdef_assert_instance(isinstance(annunciate, bool), "annunciating", bool)

        self._defaults['annunciating'] = annunciate

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def default_filter(self, expression):
        beastdef_assert_instance(isinstance(expression, str) or isinstance(expression, unicode), "expression", str)

        self._defaults['filter'] = expression

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def define_title(self, name, title):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)
        beastdef_assert_instance(isinstance(title, str) or isinstance(title, unicode), "title", str)

        self._titles[name] = xml_descape(title)

        return BEAST_BASE(self._line)


    def xml_component(self, name):
        self._alarm_tree = True
        self.component(name)
        self._alarm_tree = False


    @alarmtree_interface
    @beastdef_interface
    def component(self, name):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)

        if self._including:
            raise BEASTDefSyntaxError("Included definitions cannot (yet?) have components")

        self._pv = None

        try:
            if self._component is None:
                var = self._root_components[name]
            else:
                var = self._component.components()[name]
        except KeyError:
            var = BEAST_COMPONENT(self._line, name, self._components)

            if not self._alarm_tree:
                raise BEASTDefSyntaxError("Component '{}' (line {}) with path {} is not defined in the alarm tree".format(name,
                                                                                                                          var.lineno(),
                                                                                                                          var.strpath()))

            if self._component is not None:
                self._component.add_component(var)
            else:
                self._root_components[name] = var

        self._component = var
        self._components.append(var)

        return var


    @alarmtree_interface
    @beastdef_interface
    def include(self, devicename):
        if not self._alarm_tree:
            raise BEASTDefSyntaxError("Function is only valid during alarm tree definition")

        if self._component is None:
            raise BEASTDefSyntaxError("Cannot do includes outside of a component")

        if devicename in self._device_includes:
            raise BEASTDefSyntaxError("'{}' is already included in '{}'".format(devicename, self._device_includes[devicename].strpath(True)))

        self._device_includes[devicename] = self._component

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def include_type(self, devicetype):
        if not self._alarm_tree:
            raise BEASTDefSyntaxError("Function is only valid during alarm tree definition")

        if self._component is None:
            raise BEASTDefSyntaxError("Cannot do includes outside of a component")

        if devicetype in self._devtype_includes:
            raise BEASTDefSyntaxError("'{}' is already included in '{}'".format(devicetype, self._devtype_includes[devicetype].strpath(True)))

        self._devtype_includes[devicetype] = self._component

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def end_component(self):
        try:
            self._components.pop()
        except IndexError:
            raise BEASTDefSyntaxError("No component to end")

        self._pv = None

        if self._components:
            self._component = self._components[-1]
        else:
            self._component = None

        return BEAST_BASE(self._line)


    @beastdef_interface
    def pv(self, name, delay = 0, count = 0):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)
        beastdef_assert_instance(isinstance(delay, float) or isinstance(delay, int), "delay", float)
        beastdef_assert_instance(isinstance(count, int), "count", int)

        if self._component is None:
            raise BEASTDefSyntaxError("PV ('{}') without component!".format(name))

        if delay < 0:
            raise BEASTDefSyntaxError("'delay' must be greater (or equal) than 0")

        if count < 0:
            raise BEASTDefSyntaxError("'count' must be greater (or equal) than 0")

        if self._devicename:
            name = "{}:{}".format(self._devicename, name)

        var = BEAST_PV(self._line, name, delay, count, defaults = self._defaults)
        self._pv = var
        self._component.add_pv(var)

        return var


    @beastdef_interface
    def description(self, desc):
        beastdef_assert_instance(isinstance(desc, str) or isinstance(desc, unicode), "description", str)

        if self._pv is None:
            raise BEASTDefSyntaxError("Description without PV")

        self._pv.add_description(xml_descape(desc))

        return self._pv


    @beastdef_interface
    def disable(self, val = True):
        beastdef_assert_instance(isinstance(val, bool), "disable", bool)

        if self._pv is None:
            raise BEASTDefSyntaxError("Disable without PV")

        self._pv.disable(val)

        return self._pv


    @beastdef_interface
    def latching(self, latch):
        beastdef_assert_instance(isinstance(latch, bool), "latching", bool)

        if self._pv is None:
            raise BEASTDefSyntaxError("Latching without PV")

        self._pv.set_latching(latch)

        return self._pv


    @beastdef_interface
    def annunciating(self, annunciate):
        beastdef_assert_instance(isinstance(annunciate, bool), "annunciating", bool)

        if self._pv is None:
            raise BEASTDefSyntaxError("Annunciating without PV")

        self._pv.set_annunciating(annunciate)

        return self._pv


    @beastdef_interface
    def filter(self, expression):
        beastdef_assert_instance(isinstance(expression, str) or isinstance(expression, unicode), "expression", str)

        if self._pv is None:
            raise BEASTDefSyntaxError("Filter without PV")

        self._pv.set_filter(expression)

        return self._pv


    def _check_title_details(self, typ, title, details):
        beastdef_assert_instance(isinstance(title, str) or isinstance(title, unicode), "title", str)
        beastdef_assert_instance(isinstance(details, str) or isinstance(details, unicode), "details", str)

        if self._pv_or_component() is None:
            raise BEASTDefSyntaxError("{} without PV or component".format(typ))


    def _pv_or_component(self):
        if self._pv is None:
            return self._component

        return self._pv


    @alarmtree_interface
    @beastdef_interface
    def guidance(self, title, details):
        self._check_title_details("Guidance", title, details)

        var = BEAST_GUIDANCE(self._line, self._titles[title], details)
        self._pv_or_component().add_guidance(var)

        return var


    @alarmtree_interface
    @beastdef_interface
    def display(self, title, details):
        self._check_title_details("Display", title, details)

        var = BEAST_DISPLAY(self._line, self._titles[title], details)
        self._pv_or_component().add_display(var)

        return var


    @alarmtree_interface
    @beastdef_interface
    def command(self, title, details):
        self._check_title_details("Command", title, details)

        var = BEAST_COMMAND(self._line, self._titles[title], details)
        self._pv_or_component().add_command(var)

        return var


    @alarmtree_interface
    @beastdef_interface
    def automated_action(self, title, details, delay = 0):
        self._check_title_details("Automated action", title, details)
        beastdef_assert_instance(isinstance(delay, int), "delay", int)

        var = BEAST_AUTOMATED_ACTION(self._line, self._titles[title], details, delay)
        self._pv_or_component().add_automated_action(var)

        return var





if __name__ == "__main__":
    class FakeDevice:
        def name(self):
            return "FakeDevice"

    try:
        bf_def = BEAST_DEF()
        bf_def.parse(sys.argv[1], FakeDevice())
    except BEASTDefException as e:
        print(e, file = sys.stderr)
