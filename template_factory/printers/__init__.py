import glob
import importlib
import os.path



def get_printer(printer):
    for (n, c) in _available_printers:
        if n is not None and n == printer:
            return c()
    assert False, "No such printer: " + printer
    return None


def available_printers():
    printers = []
    for (n, c) in _available_printers:
        printers.append(n)

    return printers




from tf_ifdef import IF_DEF

#
# PRINTER
#
class PRINTER(object):
    def __init__(self, comments = True):
        assert isinstance(comments, bool),    func_param_msg("comments", "bool")

        self._output   = None
        self._comments = comments
        pass


    def _check_if_list(self, output):
        assert isinstance(output, list),    func_param_msg("output", "list")


    def plcf(self, plcf_expr):
        assert isinstance(plcf_expr, str),    func_param_msg("plcf_expr", "str")

        return "[PLCF#{plcf}]".format(plcf = plcf_expr)


    def comment(self):
        return ""


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


    def _append(self, gen, output = None):
        # the generic format is ("input", "result")
        # but lets support "result" only formats too
        if not isinstance(gen, tuple):
            from_inp = ""
            result = gen
        else:
            (from_inp, result) = gen

        if output is None:
            output = self._output

        if from_inp is None:
            from_inp = ""

        if output is not None and gen != ("", ""):
            if self._comments and from_inp != "":
                # empty lines are special
                if from_inp.strip() != "":
                    output.append(self.comment() + from_inp)
                else:
                    output.append(from_inp)
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
