from __future__ import print_function
from __future__ import absolute_import

import glob
import importlib
import os.path



def get_printer(printer):
    for (n, c) in _available_printers:
        if n is not None and n == printer:
            return c()

    return None


def available_printers():
    printers = []
    for (n, c) in _available_printers:
        printers.append(n)

    return printers


def is_combinable(printer):
    return printer in _combinable_printers




from tf_ifdef import IF_DEF, SOURCE, PRINTER_METADATA

#
# PRINTER
#
class PRINTER(object):
    def __init__(self, comments = False, preserve_empty_lines = False, show_origin = False):
        assert isinstance(comments,             bool),    func_param_msg("comments",             "bool")
        assert isinstance(preserve_empty_lines, bool),    func_param_msg("preserve_empty_lines", "bool")
        assert isinstance(show_origin,          bool),    func_param_msg("show_origin",          "bool")

        self._output         = None
        self._comments       = comments
        self._preserve_empty = preserve_empty_lines
        self._show_origin    = show_origin


    def _check_if_list(self, output):
        assert isinstance(output, list),    func_param_msg("output", "list")


    def plcf(self, plcf_expr):
        assert isinstance(plcf_expr, str),    func_param_msg("plcf_expr", "str")

        return "[PLCF#{plcf}]".format(plcf = plcf_expr)


    def inst_slot(self, if_def = None):
        if if_def is not None:
            return if_def.inst_slot()

        return self.plcf("INSTALLATION_SLOT")


    def root_inst_slot(self):
        return self.plcf("ROOT_INSTALLATION_SLOT")


    def template(self):
        return self.plcf("TEMPLATE")


    def timestamp(self):
        return self.plcf("TIMESTAMP")


    def add_filename_header(self, output, inst_slot = None, template = True, extension = 'txt', custom = None):
        if custom:
            self._append("#FILENAME {custom}".format(custom = custom), output)
            return

        if inst_slot is None:
            inst_slot = self.root_inst_slot()

        if template is True:
            template = "-{}".format(self.template())
        elif template:
            template = "-{}".format(template)
        else:
            template = ""


        self._append("#FILENAME {inst_slot}{template}-{timestamp}.{ext}".format(inst_slot = inst_slot,
                                                                                template  = template,
                                                                                timestamp = self.timestamp(),
                                                                                ext       = extension), output)


    def modulename(self):
        return self.plcf("ext.eee_modulename()")


    def snippet(self):
        return self.plcf("ext.snippet()")


    def comment(self):
        return ""


    def origin(self):
        return "<<<--- "


    def empty_line(self):
        return "\n"


    @staticmethod
    def name():
        """Return the *globally unique* name of the printer."""
        return ""


    @staticmethod
    def combinable():
        """Return if the printer can be used with DEFs and ordinary templates.

           A printer is combinable if the result can be the combination of processing DEFs
           and ordinary templates. Most printers are non-combinable.

        """
        return False


    def write(self, fname, output):
        self._check_if_list(output)

        gen_fname = "{basename}_TEMPLATE_{printer}.txt"
        with open(gen_fname.format(basename = os.path.splitext(os.path.basename(fname))[0], printer = self.name()), "w") as f:
            for line in output:
                if line is not None:
                    print(line.rstrip(), file = f)


    def needs_ifdef(self):
        # Check if _any_body() is overridden
        return "_any_body" not in self.__class__.__dict__


    def header(self, output, **keyword_params):
        self._check_if_list(output)

        return self


    def body(self, if_def, output, **keyword_params):
        self._check_if_list(output)

        if isinstance(if_def, IF_DEF):
            self._ifdef_body(if_def, output, **keyword_params)
        else:
            self._any_body(output, **keyword_params)


    def _ifdef_body(self, if_def, output, **keyword_params):
        pass


    def _any_body(self, output, **keyword_params):
        pass


    def footer(self, output, **keyword_params):
        self._check_if_list(output)

        return self


    def _append_origin(self, origin, output):
        if self._show_origin and origin.strip() != "":
            output.extend(map(lambda x: self.comment() + self.origin() + x, origin.splitlines()))


    def _append_source(self, source, output):
        if isinstance(source, PRINTER_METADATA) and source.get(self.name()) is not None:
            self._append_origin(source.source(), output)
            self._append(str(source.get(self.name())), output)
            return

        if source.is_comment():
            if self._comments:
                if source.source().strip() != "":
                    output.append(self.comment() + source.source())
                elif self._preserve_empty:
                    output.append(self.empty_line())
        else:
            self._append_origin(source.source(), output)


    def _append(self, gen, output = None):
        if output is None:
            output = self._output

        if output is None:
            return

        if isinstance(gen, SOURCE):
            return self._append_source(gen, output)

        # the generic format is ("input", "result")
        # but lets support "result" only formats too
        if not isinstance(gen, tuple):
            from_inp = ""
            result = gen
        else:
            (from_inp, result) = gen

        if from_inp is None:
            from_inp = ""

        assert isinstance(result, str)
        self._append_origin(from_inp, output)
        if result != "":
            output += result.splitlines(True)

        return gen


    def call(self, var, func):
        return self._append(getattr(var, func + self.__class__.__name__)())




_available_printers  = []
_combinable_printers = set()
for printer in glob.iglob(os.path.dirname(__file__) + "/printer_*.py"):
    mod = os.path.splitext(os.path.basename(printer))[0]
    importlib.import_module(__name__ + "." + mod)

    try:
        prn_tpl = eval(mod + ".printer()")
        if type(prn_tpl) is list:
            _available_printers.extend(prn_tpl)
            for (n, c) in prn_tpl:
                if c.combinable():
                    _combinable_printers.add(n)
        else:
            _available_printers.append(prn_tpl)
            if prn_tpl[1].combinable():
                _combinable_printers.add(prn_tpl[0])
    except NotImplementedError:
        pass

    del mod
    del printer


del glob
del importlib
