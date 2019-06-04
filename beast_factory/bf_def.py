from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

""" BEAST Factory: Alarm Definition Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019, European Spallation Source, Lund"
__license__    = "GPLv3"


from collections import OrderedDict
import codecs
import helpers



def xml_descape(string):
    return string.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")



class BEASTDefException(Exception):
    args_format = """
{}
"""

    def __init__(self, typemsg, *args, **keyword_params):
        self.typemsg        = typemsg
        self.args           = args
        self.keyword_params = keyword_params


    def __call__(self, *args):
        return self.__class__(self.typemsg, *(self.args + args))


    def __repr__(self):
        try:
            return """{error} at line {linenum}: {line}{args}""".format(error   = self.typemsg,
                                                                        linenum = self.keyword_params["linenum"],
                                                                        line    = self.keyword_params["line"],
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



class BEASTDefFeatureMissingError(BEASTDefException):
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



class BEAST_COMPONENT(BEAST_BASE):
    def __init__(self, line, name, path):
        super(BEAST_COMPONENT, self).__init__(line)

        self._name     = name
        self._path     = list(path)
        self._children = OrderedDict()
        self._pvs      = []


    def __repr__(self):
        return self._name


    def __str__(self):
        return self._name


    def name(self):
        return self._name


    def components(self):
        return self._children


    def pvs(self):
        return self._pvs


    def path(self):
        return self._path


    def xpath(self):
        return "{}/component[@name='{}']".format("".join(["/component[@name='{}']".format(i.name()) for i in self._path]), self._name)


    def add_component(self, child):
        beastdef_assert_instance(isinstance(child, BEAST_COMPONENT), "child", BEAST_COMPONENT)

        try:
            if self._children[child.name()] != child:
                raise BEASTDefSyntaxError("Component ('{}') is already defined at this level".format(child.name()))
        except KeyError:
            pass

        self._children[child.name()] = child


    def add_pv(self, pv):
        beastdef_assert_instance(isinstance(pv, BEAST_PV), "child", BEAST_PV)

        self._pvs.append(pv)


    def toxml(self, parent, etree):
        element = etree.SubElement(parent, "component", name = self._name)

        for pv in self.pvs():
            pv.toxml(element, etree)

        for child in self._children.itervalues():
            child.toxml(element, etree)

        return element



class BEAST_PV(BEAST_BASE):
    def __init__(self, line, name, defaults):
        super(BEAST_PV, self).__init__(line)

        self._name     = name
        self._desc     = None

        self._enabled      = defaults['enabled']
        self._latching     = defaults['latching']
        self._annunciating = defaults['annunciating']

        self._guidances         = []
        self._displays          = []
        self._commands          = []
        self._automated_actions = []


    def __repr__(self):
        return self._name


    def toxml(self, parent, etree):
        element = etree.SubElement(parent, "pv", name = self._name)

        if self._desc is not None:
            etree.SubElement(element, "description").text = self._desc

        etree.SubElement(element, "enabled").text      = str(self._enabled).lower()
        etree.SubElement(element, "latching").text     = str(self._latching).lower()
        etree.SubElement(element, "annunciating").text = str(self._annunciating).lower()

        def xmllist(ls, etree):
            for guidance in ls:
                guidance.toxml(element, etree)

        xmllist(self._guidances, etree)
        xmllist(self._commands, etree)
        xmllist(self._displays, etree)
        xmllist(self._automated_actions, etree)

        return element


    def name(self):
        return self._name


    def description(self):
        return self._desc


    def add_description(self, desc):
        self._desc = desc


    def set_latching(self, latching):
        self._latching = latching


    def set_annunciating(self, annunciating):
        self._annunciating = annunciating


    def add_guidance(self, guidance):
        self._guidances.append(guidance)


    def add_display(self, display):
        self._displays.append(display)


    def add_command(self, command):
        self._commands.append(command)


    def add_automated_action(self, automated_action):
        self._automated_actions.append(automated_action)



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
            raise BEASTDefException("Trying to call non-interface function '{f}'".format(f = func.__name__))

    return beastdef_interface_func



class BEAST_DEF(object):
    def __init__(self, etree, **keyword_params):
        # Current component and pv
        self._component = None
        self._pv        = None

        # Path to current component
        self._components      = []
        # Root components
        self._root_components = OrderedDict()

        # Not defining alarm tree
        self._alarm_tree = False

        # Defined titles to be used in guidance/display/command/automated_action
        self._titles = dict()

        # Default and titles defined in the alarm tree
        self._global_titles   = dict()
        self._global_defaults = { 'enabled'      : True,
                                  'latching'     : True,
                                  'annunciating' : False,
                                }

        # The ElementTree implementation
        self._etree = etree

        # The config name
        self._config = None

        # The PV name has to be prefixed
        self._devicename = None

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


    def _eval(self, line, linenum):
        keyword = line.split('(')[0]
        if keyword not in self._evalEnv:
            raise BEASTDefSyntaxError("Not supported keyword: '{}'".format(keyword))

        try:
            result = eval(line, self._evalEnv)
        except NameError as e:
            raise BEASTDefSyntaxError(e)

        if not isinstance(result, BEAST_DEF_INTERFACE_FUNC):
           raise BEASTDefSyntaxError("Missing parentheses?")


    def _reset(self):
        self._devicename = None
        self._component  = None
        self._pv         = None
        self._components = []
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

            self._eval(stripped_line, linenum)
        except BEASTDefException as e:
            e.add_params(line = stripped_line, linenum = linenum)
            raise e
        except AssertionError as e:
            raise BEASTDefInternalError(e, line = stripped_line, linenum = linenum)
        except SyntaxError as e:
            raise BEASTDefSyntaxError(e.msg, line = stripped_line, linenum = linenum)


    def parse_alarm_tree(self, def_file, config = None):
        if self._root_components:
            raise BEASTDefSyntaxError("Alarm tree is already defined!")

        self._alarm_tree = True

        with codecs.open(def_file, 'r', encoding = 'utf-8') as defs:
            linenum = 1
            for line in defs:
                self._parse(line, linenum)
                linenum += 1

        # Save defined titles and defaults
        self._global_defaults = self._defaults
        self._global_titles   = self._titles

        if config is not None:
            self._config = config

        if self._config is None:
            raise BEASTDefSyntaxError("No config name is defined in alarm tree and no --config option was specified")

        self._alarm_tree = False


    def parse(self, def_file, device = None):
        self._reset()

        if def_file.endswith('.alarms-template') and device:
            self._devicename = device.name()

        with codecs.open(def_file, 'r', encoding = 'utf-8') as defs:
            linenum = 1
            for line in defs:
                self._parse(line, linenum)
                linenum += 1


    def toxml(self):
        xml_tree = self._etree.ElementTree(self._etree.Element('config'))
        root     = xml_tree.getroot()
        root.tag = "config"
        root.attrib.clear()
        root.attrib['name'] = self._config

        for component in self.components().itervalues():
            component.toxml(root, etree = self._etree)

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
    def define_title(self, name, title):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)
        beastdef_assert_instance(isinstance(title, str) or isinstance(title, unicode), "title", str)

        self._titles[name] = xml_descape(title)

        return BEAST_BASE(self._line)


    @alarmtree_interface
    @beastdef_interface
    def component(self, name):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)

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
                                                                                                                          var.path()))

            if self._component is not None:
                self._component.add_component(var)
            else:
                self._root_components[name] = var

        self._component = var
        self._components.append(var)

        return var


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
    def pv(self, name):
        beastdef_assert_instance(isinstance(name, str) or isinstance(name, unicode), "name", str)

        if self._component is None:
            raise BEASTDefSyntaxError("PV ('{}') without component!".format(name))

        if self._devicename:
            name = "{}:{}".format(self._devicename, name)

        var = BEAST_PV(self._line, name, defaults = self._defaults)
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


    def _check_title_details(self, typ, title, details):
        beastdef_assert_instance(isinstance(title, str) or isinstance(title, unicode), "title", str)
        beastdef_assert_instance(isinstance(details, str) or isinstance(details, unicode), "details", str)

        if self._pv is None:
            raise BEASTDefSyntaxError("{} without PV".format(typ))


    @beastdef_interface
    def guidance(self, title, details):
        self._check_title_details("Guidance", title, details)

        var = BEAST_GUIDANCE(self._line, self._titles[title], details)
        self._pv.add_guidance(var)

        return var


    @beastdef_interface
    def display(self, title, details):
        self._check_title_details("Display", title, details)

        var = BEAST_DISPLAY(self._line, self._titles[title], details)
        self._pv.add_display(var)

        return var


    @beastdef_interface
    def command(self, title, details):
        self._check_title_details("Command", title, details)

        var = BEAST_COMMAND(self._line, self._titles[title], details)
        self._pv.add_command(var)

        return var


    @beastdef_interface
    def automated_action(self, title, details, delay):
        self._check_title_details("Automated action", title, details)
        beastdef_assert_instance(isinstance(delay, float), "delay", float)

        var = BEAST_AUTOMATED_ACTION(self._line, self._titles[title], details, delay)
        self._pv.add_automated_action(var)

        return var





if __name__ == "__main__":
    pass
