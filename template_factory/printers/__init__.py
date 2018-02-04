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


    def inst_slot(self):
        return self.plcf("INSTALLATION_SLOT")


    def template(self):
        return self.plcf("TEMPLATE")


    def timestamp(self):
        return self.plcf("TIMESTAMP")


    def comment(self):
        return ""


    def origin(self):
        return "<<<--- "


    def empty_line(self):
        return "\n"


    @staticmethod
    def name():
        return ""


    def write(self, fname, output):
        self._check_if_list(output)

        gen_fname = "{basename}_TEMPLATE_{printer}.txt"
        with open(gen_fname.format(basename = os.path.splitext(fname)[0], printer = self.name()), "w") as f:
            for line in output:
                if line is not None:
                    f.write(line)


    def header(self, output):
        self._check_if_list(output)

        return self


    def body(self, if_def, output):
        assert isinstance(if_def, IF_DEF),  func_param_msg("if_def", "IF_DEF")
        self._check_if_list(output)

        return self


    def footer(self, output):
        self._check_if_list(output)

        return self


    def _append_origin(self, origin, output = None):
        if self._show_origin and origin.strip() != "":
            output.append(self.comment() + self.origin() + origin)

    def _append_source(self, source, output = None):
        if isinstance(source, PRINTER_METADATA) and source.get(self.name()) is not None:
            self._append_origin(source, output)
            self._append(str(source.get(self.name())), output)

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




_available_printers = []
for printer in glob.iglob(os.path.dirname(__file__) + "/printer_*.py"):
    mod = os.path.splitext(os.path.basename(printer))[0]
    importlib.import_module(__name__ + "." + mod)

    try:
        prn_tpl = eval(mod + ".printer()")
        if type(prn_tpl) is list:
            _available_printers.extend(prn_tpl)
        else:
            _available_printers.append(prn_tpl)
    except NotImplementedError:
        pass

    del mod
    del printer


del glob
del importlib
