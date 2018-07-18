from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

""" Template Factory: Interface Definition Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


import copy
from collections import OrderedDict
#import inspect
import hashlib



inpv_template  = """record({recordtype}, "{inst_slot}:{name}")
{{{alias}
	field(SCAN, "I/O Intr")
	field(DTYP, "S7plc")
	field(INP,  "@$(PLCNAME)/{offset} T={var_type}{link_extra}")
	field(DISS, "INVALID")
	field(DISV, "0")
	field(SDIS, "[PLCF#ROOT_INSTALLATION_SLOT]:PLCHashCorrectR"){pv_extra}
}}

"""
test_inpv_template  = """record({recordtype}, "{inst_slot}:{name}")
{{{alias}
	{pv_extra}
}}

"""


outpv_template = """record({{recordtype}}, "{{inst_slot}}:{{name}}")
{{{{{{alias}}
	field(DTYP, "{asyntype}")
	field(OUT,  "@{asynio}($(PLCNAME)write, {{offset}}, {{link_extra}}){{var_type}}")
	field(DISS, "INVALID")
	field(DISV, "0")
	field(SDIS, "[PLCF#ROOT_INSTALLATION_SLOT]:PLCHashCorrectR"){{pv_extra}}
}}}}

"""
test_outpv_template = """record({{recordtype}}, "{{inst_slot}}:{{name}}")
{{{{{{alias}}
	{{pv_extra}}
}}}}

"""






# Data types for S7 PLCs
PLC_types = { 'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'SSTIME', 'TIME', 'LTIME', 'DATE', 'TIME_OF_DAY', 'CHAR' }

# New data types for S7-1200/1500
PLC_types.update({ 'USINT', 'SINT', 'UINT', 'UDINT' })


bits_in_type_map = { 'UINT8'   :  8, 'INT8'   :  8, 'UNSIGN8' :  8, 'BYTE'       :  8, 'CHAR'       :  8, 'USINT'    :  8, 'SINT'         :  8,
                     'UINT16'  : 16, 'INT16'  : 16, 'SHORT'   : 16, 'UNSIGN16'   : 16, 'WORD'       : 16, 'INT16SM'  : 16, 'BCD_UNSIGNED' : 16, 'BCD_SIGNED' : 16, 'INT'  : 16, 'UINT'  : 16,
                     'UINT32'  : 32, 'INT32'  : 32, 'LONG'    : 32, 'UNSIGN32'   : 32, 'DWORD'      : 32, 'INT32_LE' : 32, 'INT32_BE'     : 32, 'DINT'       : 32, 'TIME' : 32, 'UDINT' : 32,
                     'FLOAT32' : 32, 'REAL32' : 32, 'FLOAT'   : 32, 'FLOAT32_LE' : 32, 'FLOAT32_BE' : 32, 'REAL'     : 32,
                     'FLOAT64' : 64, 'REAL64' : 64, 'DOUBLE'  : 64, 'FLOAT64_LE' : 64, 'FLOAT64_BE' : 64,
                     'STRING'  : 40 * 8 }


class IfDefException(Exception):
    def __init__(self, typemsg, *args):
        self.typemsg = typemsg
        self.args    = args


    def __call__(self, *args):
        return self.__class__(self.typemsg, *(self.args + args))


    def type(self):
        return self.typemsg


class IfDefSyntaxError(IfDefException):
    def __init__(self, *args):
        IfDefException.__init__(self, "Syntax error", *args)


class IfDefInternalError(IfDefException):
    def __init__(self, *args):
        IfDefException.__init__(self, "Internal error", *args)



#def ifdef_assert_instance(var, var_type, var_type_string = None):
#    frame  = inspect.currentframe()
#    oframe = frame.f_back
#    try:
#        all_vars = oframe.f_locals
#        if var_type_string is None:
#            var_type_string = str(var_type)
#        if not isinstance(all_vars[var], var_type):
#            raise IfDefInternalError("'{param}' must be of type {type}!".format(param = var, type = var_type_string))
#    finally:
#        del oframe
#        del frame




class DummyHash(object):
    def __init__(self):
        pass


    def update(self, string):
        pass



class SOURCE(object):
    def __init__(self, source, comment = False):
        if isinstance(source, tuple):
            source, sourcenum = source
        else:
            sourcenum = -1

        assert isinstance(source,     str),  func_param_msg("source",     "string")
        assert isinstance(sourcenum,  int),  func_param_msg("sourcenum",  "integer")
        assert isinstance(comment,    bool), func_param_msg("comment",    "bool")

        self._source    = source.lstrip()
        self._sourcenum = sourcenum
        self._comment   = comment
        self._warnings  = None


    def is_comment(self):
        return self._comment


    def source(self):
        return self._source


    def sourcenum(self):
        return self._sourcenum


    def warnings(self):
        return self._warnings


    def _add_warning(self, warn):
        if self._warnings is None:
            self._warnings = [ "At line number {lnum}:".format(lnum = self.sourcenum()), warn ]
        else:
            self._warnings.append(warn)

        return warn



class PRINTER_METADATA(SOURCE):
    def __init__(self, source, printers, metadata):
        if isinstance(printers, str):
            printers = [ printers ]
        assert isinstance(printers, list), func_param_msg("printers", "list")

        SOURCE.__init__(self, source)

        self._printers = printers
        self._metadata = metadata


    def get(self, printer):
        if printer not in self._printers:
            return None

        return self._metadata



class VERBATIM(SOURCE):
    def __init__(self, source, verbatim):
        assert isinstance(source, tuple),  func_param_msg("source",   "tuple")
        assert isinstance(verbatim, str),  func_param_msg("verbatim", "string")

        SOURCE.__init__(self, source)

        self._verbatim = verbatim


    def __str__(self):
        return self._verbatim



#
# Blocks
#
class BLOCK(SOURCE):
    STATUS = "STATUS"
    CMD    = "COMMAND"
    PARAM  = "PARAMETER"

    def __init__(self, source, block_type, optimize):
        SOURCE.__init__(self, source)

        BITS.end()

        assert isinstance(block_type,    str)
        assert isinstance(optimize,      bool)
        self._block_type    = block_type

        self._block_offset  = 0
        self._length        = 0
        self._optimize_s7db = optimize


    def _is_alignment_needed(self, width):
        if not self.optimize():
            return (self._block_offset % 2) == 1
        else:
            # MODBUS cannot address the individual bytes in a WORD
            return (self.is_cmd_block() or self.is_param_block() or width > 1) and (self._block_offset % 2) == 1


    def endian_correct_epics_type(self, epics_type):
        return epics_type


    def optimize(self):
        return self._optimize_s7db


    def length(self):
        return self._length


    def offset_for(self, width):
        if self._is_alignment_needed(width):
            self._block_offset += 1
        return self._block_offset


    def get_overlap(self):
        return OVERLAP(self)


    def is_status_block(self):
        return isinstance(self, STATUS_BLOCK)


    def is_cmd_block(self):
        return isinstance(self, CMD_BLOCK)


    def is_param_block(self):
        return isinstance(self, PARAM_BLOCK)


    def type(self):
        return self._block_type


    def plc_type_to_epics_type(self, plc_type):
        try:
            return self.valid_type_pairs()[plc_type][0]
        except KeyError:
            if plc_type in PLC_types:
                raise IfDefSyntaxError("Unsupported PLC type: " + plc_type)
            else:
                raise IfDefSyntaxError("Unknown PLC type: " + plc_type)


    def pair_types(self, keyword_params):
        if keyword_params is None:
            return (None, None)

        assert isinstance(keyword_params, dict), func_param_msg("keyword_params", "dict")

        def _valid_var_types(self):
            types = []
            for k,v in self.valid_type_pairs().iteritems():
                types += v
            return types


        for key, value in keyword_params.iteritems():
            if key.startswith(BASE_TYPE.PV_PREFIX) or not key in PLC_types:
                continue

            if not value in _valid_var_types(self):
                raise IfDefSyntaxError("Unsupported type: " + value)

            plcbits   = _bits_in_type(key)
            epicsbits = _bits_in_type(value)

            if not plcbits == epicsbits:
                raise IfDefSyntaxError("Bit width must be the same: {plc} vs {epics}".format(plc = key, epics = value))

            return (key, value)

        return (None, None)


    def end(self):
        BITS.end()
        if self._block_offset % 2:
            self._block_offset += 1

        self._length = self._block_offset


    def pv_template(self, test = False, asyntype = None, asynio = None):
        if test:
            pv_templates = { BLOCK.CMD : test_outpv_template,   BLOCK.PARAM : test_outpv_template,   BLOCK.STATUS : test_inpv_template }
        else:
            pv_templates = { BLOCK.CMD : outpv_template,   BLOCK.PARAM : outpv_template,   BLOCK.STATUS : inpv_template }
        pv_temp = pv_templates[self.type()]

        if not self.is_status_block():
            assert isinstance(asyntype, str), func_param_msg("asyntype", "string")
            assert isinstance(asynio,   str), func_param_msg("asynio",   "string")

            return pv_temp.format(asyntype = asyntype, asynio = asynio)
        return pv_temp


    def compute_offset(self, num_bytes):
        if isinstance(num_bytes, int):
            self._block_offset += num_bytes
        else:
            raise IfDefSyntaxError("Unknown type: " + str(num_bytes))



class STATUS_BLOCK(BLOCK):
    @staticmethod
    def length_keyword():
        return "StatusWordsLength"


    @staticmethod
    def counter_keyword():
        return "Counter2"


    @staticmethod
    def root_of_db():
        return "^(PLCToEPICSDataBlockStartOffset)"


    @staticmethod
    def valid_type_pairs():
        return dict(BYTE  = [ "UINT8",   "UNSIGN8", "BYTE", "CHAR" ],
                    USINT = [ "UINT8",   "UNSIGN8", "BYTE", "CHAR" ],
                    SINT  = [ "INT8" ],
                    WORD  = [ "UINT16",  "UNSIGN16", "WORD" ],
                    UINT  = [ "UINT16",  "UNSIGN16", "WORD" ],
                    INT   = [ "INT16",   "SHORT" ],
                    DWORD = [ "UINT32",  "UNSIGN32", "DWORD" ],
                    UDINT = [ "UINT32",  "UNSIGN32", "DWORD" ],
                    DINT  = [ "INT32",   "LONG" ],
                    REAL  = [ "FLOAT32", "REAL32",   "FLOAT" ],
                    TIME  = [ "INT32",   "LONG" ])


    def __init__(self, source, optimize):
        BLOCK.__init__(self, source, BLOCK.STATUS, optimize)


    def link_offset(self, var):
        offset_template = "[PLCF# ( {root} + {counter} ) * 2 + {offset}]"
        return offset_template.format(root = self.root_of_db(), counter = self.counter_keyword(), offset = var.offset())



#
# Special class to handle the similarities between CMD_BLOCK and PARAM_BLOCK
#
class MODBUS(object):
    _endian_dependent_type_pairs = dict(
# DWORD and UDINT are unsigned types, but MODBUS does not support writing (or reading) unsigned 32bit integers
# so make it an error to use them
#                    DWORD = [ "INT32_BE",   "INT32_LE" ],
#                    UDINT = [ "INT32_BE",   "INT32_LE" ],
                    DINT  = [ "INT32_BE",   "INT32_LE" ],
                    REAL  = [ "FLOAT32_BE", "FLOAT32_LE" ],
                    TIME  = [ "INT32_BE",   "INT32_LE" ])


    _valid_type_pairs = dict(_endian_dependent_type_pairs,
                    BYTE  = [ "UINT16" ],
                    USINT = [ "UINT16" ],
                    SINT  = [ "INT16" ],
                    WORD  = [ "UINT16",     "BCD_UNSIGNED" ],
                    UINT  = [ "UINT16",     "BCD_UNSIGNED" ],
                    INT   = [ "INT16",      "BCD_SIGNED",  "INT16SM" ])


    _endian_specific_epics_types = [item for sublist in _endian_dependent_type_pairs.values() for item in sublist]

    @staticmethod
    def counter_keyword():
        return "Counter1"


    @staticmethod
    def root_of_db():
        return "^(EPICSToPLCDataBlockStartOffset)"


    @staticmethod
    def endian_dependent_type_pairs():
        return MODBUS._endian_dependent_type_pairs


    @staticmethod
    def valid_type_pairs():
        return MODBUS._valid_type_pairs


    def endian_correct_epics_type(self, epics_type):
        if epics_type not in self._endian_specific_epics_types:
            return super(MODBUS, self).endian_correct_epics_type(epics_type)

        return epics_type[0:-2] + "[PLCF#'BE' if '^(PLC-EPICS-COMMS:Endianness)' == 'BigEndian' else 'LE']"


    def link_offset(self, var):
        offset_template = "[PLCF# ( {root} + {counter} ) + {offset}]"
        return offset_template.format(root = self.root_of_db(), counter = self.counter_keyword(), offset = var.offset() // 2)




class CMD_BLOCK(MODBUS, BLOCK):
    @staticmethod
    def length_keyword():
        return "CommandWordsLength"


    def __init__(self, source, optimize):
        BLOCK.__init__(self, source, BLOCK.CMD, optimize)



class PARAM_BLOCK(MODBUS, BLOCK):
    @staticmethod
    def length_keyword():
        return "ParameterWordsLength"


    def __init__(self, source, optimize):
        BLOCK.__init__(self, source, BLOCK.PARAM, optimize)



class OVERLAP(BLOCK):
    def __init__(self, block):
        assert isinstance(block, BLOCK), func_param_msg("block", "BLOCK")

        self._block                    = block
        self._overlap_offset           = block._block_offset
        self._overlap_width            = 0
        self._overlap_alignment_needed = False

        #
        # Copy every attribute from the passed in BLOCK instance
        #
        for attr in block.__dict__:
            self.__dict__[attr] = copy.copy(block.__dict__[attr])

        #
        # Call BLOCK methods of the passed in BLOCK type instead of self
        #  but honor overriden functions
        #
        for attr in dir(block):
            val = getattr(block, attr)
            if not hasattr(val, '__call__') or attr.startswith('__') or attr in OVERLAP.__dict__:
                continue

            setattr(self, attr, val)


    def is_empty(self):
        return self._overlap_width == 0


    def offset_for(self, width):
        #
        # Check for alignment errors
        #
        if not self._block._block_offset == self._overlap_offset:
            raise IfDefInternalError("Consistency error: block is " + str(self._block._block_offset) + " while overlap is " + str(self._overlap_offset))
        if self.is_empty():
            self._overlap_alignment_needed = self._is_alignment_needed(width)
        elif self._overlap_alignment_needed != self._is_alignment_needed(width):
            raise IfDefInternalError("Alignment mismatch during overlap")

        return self._overlap_offset


    def compute_offset(self, num_bytes):
        if self._overlap_width < num_bytes:
            self._overlap_width = num_bytes


    def get_overlap(self):
        raise IfDefSyntaxError("Cannot nest overlaps!")


    def end(self):
        self._block.compute_offset(self._overlap_width)




class IF_DEF_INTERFACE_FUNC(object):
    def __init__(self, hashed):
        self._hashed = hashed


def hashed_interface(func):
    def hashed_interface_func(*args, **kwargs):
        return ifdef_interface(func)(*args, _hashed_interface = True, **kwargs)

    return hashed_interface_func


def ifdef_interface(func):
    def ifdef_interface_func(*args, **kwargs):
        if args is not None and isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], IF_DEF):
            _hashed_interface = kwargs.pop("_hashed_interface", False)
            func(*args, **kwargs)
            return IF_DEF_INTERFACE_FUNC(_hashed_interface)
        else:
            raise IfDefException("Trying to call non-interface function {f}".format(f = func.__name__))

    return ifdef_interface_func



class IF_DEF(object):
    def __init__(self, OPTIMIZE = False, HASH = None, **keyword_params):
        assert isinstance(OPTIMIZE, bool)

        if HASH is None:
            HASH = DummyHash()
        elif "update" not in dir(HASH) or not callable(HASH.update):
            raise IfDefException("Expected a hash object from the hashlib module!")

        BASE_TYPE.init()

        self._ifaces                = []
        self._STATUS                = None
        self._CMD                   = None
        self._PARAM                 = None
        self._active_BLOCK          = None
        self._overlap               = None
        self._active                = True
        self._source                = ""
        self._properties            = OrderedDict()
        self._to_plc_words_length   = 0
        self._from_plc_words_length = 0
        self._hash                  = HASH
        self._optimize              = OPTIMIZE
        self._plc_array             = None
        self._filename              = keyword_params.get('FILENAME')
        self._inst_slot             = "[PLCF#INSTALLATION_SLOT]"

        self._properties[CMD_BLOCK.length_keyword()]    = 0
        self._properties[PARAM_BLOCK.length_keyword()]  = 0
        self._properties[STATUS_BLOCK.length_keyword()] = 0

        self._evalEnv = dict()
        self._evalEnv['__builtins__'] = None
        self._evalEnv['True'] = True
        self._evalEnv['False'] = False
        for f in dir(self):
            val = getattr(self, f)
            if not hasattr(val, '__call__') or f.startswith('_'):
                continue

            if val.func_name in ["ifdef_interface_func", "hashed_interface_func"]:
                self._evalEnv[f] = val


    def _eval(self, source, stripped_source, linenum):
        if stripped_source.split('(')[0] not in self._evalEnv:
            raise IfDefSyntaxError("Not supported keyword")

        self._source    = (source, linenum)
        try:
            result = eval(stripped_source, self._evalEnv)

            if not isinstance(result, IF_DEF_INTERFACE_FUNC):
               raise IfDefSyntaxError("Missing parentheses?")

            if result._hashed:
                self._hash.update(stripped_source)
        except AssertionError as e:
            raise IfDefInternalError(e)
        except SyntaxError as e:
            raise IfDefSyntaxError(e)
        except NameError as e:
            raise IfDefSyntaxError(e)


    def _status_block(self):
        return self._STATUS


    def _cmd_block(self):
        return self._CMD


    def _param_block(self):
        return self._PARAM


    def _active_block(self):
        if self._active_BLOCK is None:
            raise IfDefSyntaxError("Must define a block first!")

        if self._overlap is not None:
            return self._overlap

        return self._active_BLOCK


    def _active_bit_def(self):
        return BITS.get_bit_def(self._active_block())


    def _end_block(self, block):
        self._end_plc_array()

        if block is not None:
            block.end()
            self._properties[block.length_keyword()] = block.length() // 2
            print("{var}: {length}".format(var = block.length_keyword(), length = str(block.length() // 2)))


    def _add(self, var):
        assert isinstance(var, SOURCE), func_param_msg("var", "SOURCE")

        if isinstance(var, BASE_TYPE):
            self._check_plc_array(var.plc_type())

        self._ifaces.append(var)


    def _add_comment(self, line):
        assert isinstance(line, str), func_param_msg("line", "string")

        var   = SOURCE(line, comment = True)
        self._add(var)


    def _add_source(self):
        self._add(SOURCE(self._source))


    # returns the length of 'block' in (16 bit) words
    def _words_length_of(self, block):
        if block is None:
            return 0

        assert isinstance(block, BLOCK), func_param_msg("block", "BLOCK", type(block))

        return self._properties[block.length_keyword()]


    def _exception_if_active(self):
        if self._active:
            raise IfDefSyntaxError("The interface definition is still active!")


    def _end_plc_array(self):
        if self._plc_array is not None:
            self.end_plc_array()


    def _check_plc_array(self, atype):
        if self._plc_array is None:
            return

        if self._plc_array[1] is None:
            self._plc_array = (self._plc_array[0], atype)
            return
        elif self._plc_array[1] == atype:
            return

        raise IfDefSyntaxError("Array is already using {type}, cannot use {atype}".format(type = self._plc_array[1], atype = atype))


    def interfaces(self):
        self._exception_if_active()

        return self._ifaces


    def warnings(self):
        if self._filename:
            in_file = "In file {filename}".format(filename = self._filename)
            warns = ['', in_file, '=' * len(in_file)]
        else:
            warns = []

        for iface in self.interfaces():
            if iface.warnings() is not None:
                warns.extend(iface.warnings())

        return warns if len(warns) > 3 else []


    def properties(self):
        self._exception_if_active()

        return self._properties


    def to_plc_words_length(self):
        self._exception_if_active()

        return self._to_plc_words_length


    def from_plc_words_length(self):
        self._exception_if_active()

        return self._from_plc_words_length


    def inst_slot(self):
        return self._inst_slot


    def add(self, source, linenum = -1):
        if not isinstance(source, str):
            raise IfDefSyntaxError("Interface definition lines must be strings!")

        if not self._active:
            raise IfDefSyntaxError("The interface definition is no longer active!")

        stripped_source = source.strip()
        if stripped_source.startswith("_"):
            raise IfDefSyntaxError("Interface definition lines cannot start with '_'")

        if stripped_source.startswith("#TF#") or stripped_source.startswith("#-"):
            return

        if stripped_source.startswith("#"):
            self._add_comment(source[1:])
            return

        if stripped_source == "":
            self._add_comment(source)
            return

        self._eval(source, stripped_source, linenum)


    @ifdef_interface
    def define_installation_slot(self, name):
        self._inst_slot = name
        self._add_source()


    @ifdef_interface
    def define_template(self, name, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Template name must be a string!")

        BASE_TYPE.add_template(name, keyword_params)
        self._add_source()


    @hashed_interface
    def define_status_block(self):
        if self._STATUS is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._STATUS = STATUS_BLOCK(self._source, self._optimize)
        self._add(self._STATUS)


    @hashed_interface
    def define_command_block(self):
        if self._CMD is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._CMD = CMD_BLOCK(self._source, self._optimize)
        self._add(self._CMD)


    @hashed_interface
    def define_parameter_block(self):
        if self._PARAM is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._PARAM = PARAM_BLOCK(self._source, self._optimize)
        self._add(self._PARAM)


    @hashed_interface
    def define_overlap(self):
        if self._active_BLOCK is None:
            raise IfDefSyntaxError("Define block first")
        if self._overlap is not None:
            raise IfDefSyntaxError("End current overlap first")

        self._overlap = self._active_BLOCK.get_overlap()
        self._add_source()


    @hashed_interface
    def end_overlap(self):
        if self._overlap is None:
            raise IfDefSyntaxError("No overlap found")

        self._overlap.end()
        self._overlap = None
        self._add_source()


    @hashed_interface
    def define_plc_array(self, name):
        if self._plc_array is not None:
            raise IfDefSyntaxError("Nesting of arrays is not possible")

        # check if there is a block defined
        self._active_block()
        var = PRINTER_METADATA(self._source, "IFA", "DEFINE_ARRAY\n{}\n".format(name))
        self._plc_array = (name, None)
        self._add(var)


    @hashed_interface
    def end_plc_array(self):
        if self._plc_array is None:
            raise IfDefSyntaxError("No array is defined yet")

        # check if there is a block defined
        self._active_block()
        var = PRINTER_METADATA(self._source, "IFA", "END_ARRAY\n{}\n".format(self._plc_array[0]))
        self._plc_array = None
        self._add(var)


    @ifdef_interface
    def define_metadata(self, name, **keyword_params):
        pass


    @ifdef_interface
    def add_metadata(self, *params, **keyword_params):
        pass


    @hashed_interface
    def add_bit(self, name = None, **keyword_params):
        self.add_digital(name, **keyword_params)


    @hashed_interface
    def add_digital(self, name = None, **keyword_params):
        bit_def = self._active_bit_def()

        if name is None:
            if "SKIP_BITS" not in keyword_params:
                keyword_params.update(SKIP_BITS = 1)

            if len(keyword_params) != 1:
                raise IfDefSyntaxError("Skipped digitals cannot have parameters")

            BIT.skip(bit_def, keyword_params["SKIP_BITS"])
            self._add_source()
        else:
            var = BIT(self._source, bit_def, name, keyword_params)
            self._add(var)


    def _add_alarm(self, name, sevr, alarm_message, **keyword_params):
        if not sevr in [ "MINOR", "MAJOR" ]:
            raise IfDefSyntaxError("Invalid alarm severity: " + sevr)
        if not isinstance(alarm_message, str):
            raise IfDefSyntaxError("Alarm message is missing: {func}(\"{name}\", \"Short alarm message\")".format(name = name, func = "add_minor_alarm" if sevr == "MINOR" else "add_major_alarm"))

        keyword_params.update(PV_OSV  = sevr)
        if "PV_ONAM" not in keyword_params:
            keyword_params.update(PV_ONAM = alarm_message)

        var = ALARM(self._source, self._active_bit_def(), name, sevr, alarm_message, keyword_params)
        self._add(var)


    # Accept None as alarm_message, so that we could display a meaningful
    #  error message in _add_alarm() if it is not provided
    @hashed_interface
    def add_minor_alarm(self, name, alarm_message = None, **keyword_params):
        self._add_alarm(name, "MINOR", alarm_message, **keyword_params)


    @hashed_interface
    def add_major_alarm(self, name, alarm_message = None, **keyword_params):
        self._add_alarm(name, "MAJOR", alarm_message, **keyword_params)


    @hashed_interface
    def skip_bit(self):
        self.skip_digital()


    @hashed_interface
    def skip_digital(self):
        self.skip_digitals(1)


    @hashed_interface
    def skip_bits(self, num):
        self.skip_digitals(num)


    @hashed_interface
    def skip_digitals(self, num):
        if isinstance(num, str):
            num = int(num)

        if not isinstance(num, int):
            raise IfDefSyntaxError("Parameter must be a number!")

        self.add_digital(SKIP_BITS = num)


    @hashed_interface
    def add_float(self, name, plc_var_type, **keyword_params):
        self.add_analog(name, plc_var_type, **keyword_params)


    @hashed_interface
    def add_analog(self, name, plc_var_type, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")
        if not isinstance(plc_var_type, str):
            raise IfDefSyntaxError("PLC type must be a string!")

        block = self._active_block()
        var = ANALOG(self._source, block, name, plc_var_type, keyword_params)
        self._add(var)


    @hashed_interface
    def add_time(self, name, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        keyword_params[BASE_TYPE.PV_PREFIX + "EGU"] = "ms"
        self.add_analog(name, "TIME", **keyword_params)


    @hashed_interface
    def add_enum(self, name, plc_var_type = "INT", nobt = 16, shift = 0, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        block = self._active_block()
        var = ENUM(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        self._add(var)


    @hashed_interface
    def add_bitmask(self, name, plc_var_type = "INT", nobt = 16, shift = 0, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        block = self._active_block()
        var = BITMASK(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        self._add(var)


    @ifdef_interface
    def add_verbatim(self, verbatim):
        if not isinstance(verbatim, str):
            raise IfDefSyntaxError("Only strings can be copied verbatim!")

        var = VERBATIM(("add_verbatim()\n", self._source[1]), verbatim)
        self._add(var)


    @hashed_interface
    def end_bits(self):
        self.end_digitals()


    @hashed_interface
    def end_digitals(self):
        self._add_source()
        BITS.end()


    def end(self):
        if self._overlap is not None:
            raise IfDefSyntaxError("Overlap is not ended")

        self._end_block(self._cmd_block())
        self._end_block(self._param_block())
        self._end_block(self._status_block())

        self._to_plc_words_length   = str(self._words_length_of(self._cmd_block()) + self._words_length_of(self._param_block()))
        self._from_plc_words_length = str(self._words_length_of(self._status_block()))

        #
        # Move parameters after commands
        #
        if self._CMD and self._PARAM:
            cmd_length = self._CMD.length()
            for src in self._ifaces:
                if isinstance(src, BASE_TYPE):
                    src.adjust_parameter(cmd_length)

        self._hash.update(str(self._properties))

        self._active = False



#
# Types
#
class BASE_TYPE(SOURCE):
    PV_PREFIX      = "PV_"
    PV_ALIAS       = PV_PREFIX + "ALIAS"
    PV_NAME        = PV_PREFIX + "NAME"
    PV_DESC        = PV_PREFIX + "DESC"
    PV_EGU         = PV_PREFIX + "EGU"
    PV_ONAM        = PV_PREFIX + "ONAM"
    PV_ZNAM        = PV_PREFIX + "ZNAM"
    ASYN_TIMEOUT   = "100"
    templates      = dict()
    pv_names       = set()

    # (len, strict) if strict is True, the text will be truncated
    field_lengths  = { PV_NAME  : (20, False),
                       PV_ALIAS : (20, False),
                       PV_DESC  : (40, True),
                       PV_EGU   : (15, True),
                       PV_ONAM  : (25, True),
                       PV_ZNAM  : (25, True)
                    }


    @staticmethod
    def init():
        BASE_TYPE.templates = dict()
        BASE_TYPE.pv_names  = set()


    def __init__(self, source, block, name, plc_var_type, keyword_params):
        SOURCE.__init__(self, source)

        assert isinstance(block,        BLOCK),                              func_param_msg("block",          "BLOCK")
        assert isinstance(name,         str),                                func_param_msg("name",           "string")
        assert isinstance(plc_var_type, str),                                func_param_msg("plc_var_type",   "string")
        assert keyword_params is None or isinstance(keyword_params, dict),   func_param_msg("keyword_params", "dict")

        if name == "":
            raise IfDefSyntaxError("Empty name")

        self._keyword_params = keyword_params
        self._expand_templates()

        if block.is_status_block():
            reserved_params = ["DTYP", "INP", "SCAN"]
        else:
            reserved_params = ["DTYP", "OUT"]

        for param in map(lambda x: BASE_TYPE.PV_PREFIX + x, reserved_params):
            if param in self._keyword_params:
                raise IfDefSyntaxError(param + " is reserved!")

        """
           Check for PLC_TYPE="{S7PLCTYPE|MODBUSTYPE}"
        """
        (p, e) = block.pair_types(self._keyword_params)
        if p is not None:
            self._plc_type = p
        else:
            self._plc_type = plc_var_type
        if e is None:
            e = block.plc_type_to_epics_type(self._plc_type)

        self._var_type       = e

        self._block          = block
        self._name           = name
        self._width          = _bytes_in_type(self._plc_type)

        # Has to be after _width is initialized
        self._end_bits()

        if isinstance(block, OVERLAP):
            self._overlapped = not block.is_empty()
        else:
            self._overlapped = False

        self._param_offset   = 0

        self.compute_offset()

        if BASE_TYPE.PV_NAME not in self._keyword_params:
            self._keyword_params[BASE_TYPE.PV_NAME] = self._name

        self._check_pv_extra()
        self._pvname = self._keyword_params[BASE_TYPE.PV_NAME]

        if self._pvname == "":
            raise IfDefSyntaxError("Empty PV_NAME")

        if self._pvname in BASE_TYPE.pv_names:
            raise IfDefSyntaxError("PV Names must be unique")

        BASE_TYPE.pv_names.add(self._pvname)



    @staticmethod
    def add_template(name, template):
        assert isinstance(name,     str),   func_param_msg("name",     "string")
        assert isinstance(template, dict),  func_param_msg("template", "dict")

        if name in BASE_TYPE.templates:
            raise IfDefSyntaxError("Template is already defined: " + name)

        BASE_TYPE.templates[name] = template


    def _expand_templates(self):
        if "TEMPLATE" not in self._keyword_params:
            return

        tname = self._keyword_params["TEMPLATE"]
        if tname not in self.templates:
            raise IfDefSyntaxError("No such template: " + tname)

        template = self.templates[tname]
        for tkey in template.keys():
            if tkey not in self._keyword_params:
                self._keyword_params[tkey] = template[tkey]


    def _end_bits(self):
        BITS.end(self._width)


    def name(self):
        """
           The name of the variable
        """
        return self._name


    def pv_name(self):
        return self._pvname


    def var_type(self):
        return self._var_type


    def endian_correct_var_type(self):
        return self._block.endian_correct_epics_type(self.var_type())


    def plc_type(self):
        """
           The type that is used on the PLC side. One of:
            - BOOL
            - BYTE
            - INT
            - WORD
            - DINT
            - DWORD
            - REAL
            - TIME
        """
        return self._plc_type


    def pv_type(self):
        raise NotImplementedError


    def adjust_parameter(self, cmd_length):
        assert isinstance(cmd_length, int), func_param_msg("cmd_length", "int")

        if self.is_parameter():
            self._param_offset = cmd_length


    def offset(self):
        return self._offset + self._param_offset


    def is_status(self):
        return self._block.is_status_block()


    def is_command(self):
        return self._block.is_cmd_block()


    def is_parameter(self):
        return self._block.is_param_block()


    def is_overlapped(self):
        return self._overlapped


    def get_parameter(self, param_name, *val_if_not_found):
        if len(val_if_not_found):
            return self._keyword_params.get(param_name, val_if_not_found[0])

        return self._keyword_params[param_name]


    def _check_pv_extra(self):
        msg_hdr_fmt = "The {field} field of the pv is too long: "

        try:
            if self._keyword_params[BASE_TYPE.PV_ALIAS] == "" or self._keyword_params[BASE_TYPE.PV_ALIAS] == []:
                raise IfDefSyntaxError("Empty PV_ALIAS")
        except KeyError:
            pass

        for key, value in self._keyword_params.iteritems():
            if not key.startswith(BASE_TYPE.PV_PREFIX):
                continue
            try:
                (length, strict) = BASE_TYPE.field_lengths[key]
                if len(value) > length:
                    msg_hdr = msg_hdr_fmt.format(field = key)
                    if self.sourcenum() != -1:
                        print("At line number {lnum}:".format(lnum = self.sourcenum()))
                    print(self._add_warning((msg_hdr + "{value} (length: {len} / {max_len})").format(value   = value,
                                                                                                     len     = len(value),
                                                                                                     max_len = length)))
                    print(self._add_warning(" " * (len(msg_hdr) + length) + "^"))
                    if strict:
                        self._keyword_params[key] = self._keyword_params[key][:length]
            except KeyError:
                pass


    def _build_pv_extra(self):
        pv_field3 = "\tfield({key},  \"{value}\")\n"
        pv_field4 = "\tfield({key}, \"{value}\")\n"

        pv_extra_fields = "\n"
        for key in sorted(self._keyword_params.keys()):
            if key.startswith(BASE_TYPE.PV_PREFIX) and key != BASE_TYPE.PV_ALIAS and key != BASE_TYPE.PV_NAME:
                if len(key) == 6:
                    pv_field_formatter = pv_field3
                else:
                    pv_field_formatter = pv_field4
                pv_extra_fields += pv_field_formatter.format(key = key[3:], value = self._keyword_params[key])

        return pv_extra_fields.rstrip('\n')


    def _get_user_link_extra(self):
        try:
            return " " + self._keyword_params["LINK_EXTRA"]
        except KeyError:
            return ""


    def _build_pv_alias(self):
        fmt = "\talias(\"{{inst_slot}}:{alias}\")"
        if BASE_TYPE.PV_ALIAS in self._keyword_params:
            if isinstance(self._keyword_params[BASE_TYPE.PV_ALIAS], str):
                return fmt.format(alias = self._keyword_params[BASE_TYPE.PV_ALIAS])
            return "\n".join([''] + map(lambda alias : fmt.format(alias = alias), self._keyword_params[BASE_TYPE.PV_ALIAS]) + [''])

        return ""

    def toEPICS(self, inst_slot = "[PLCF#INSTALLATION_SLOT]", test = False):
        return (self.source(),
                self.pv_template(test = test).format(recordtype = self.pv_type(),
                                                     inst_slot  = inst_slot,
                                                     name       = self.pv_name(),
                                                     alias      = self._build_pv_alias().format(inst_slot = inst_slot),
                                                     offset     = self.link_offset(),
                                                     var_type   = self.endian_correct_var_type(),
                                                     link_extra = self.link_extra() + self._get_user_link_extra(),
                                                     pv_extra   = self._build_pv_extra()))


    def bit_number(self):
        return 0


    def block_type(self):
        return self._block.type()


    def compute_offset(self):
        self._offset = self._block.offset_for(self._width)
        self._block.compute_offset(self._width)


    def link_offset(self):
        return self._block.link_offset(self)


    def pv_template(self, test = False, asyntype = "asynInt32", asynio = "asyn"):
        return self._block.pv_template(test = test, asyntype = asyntype, asynio = asynio)


    def link_extra(self):
        link_extra_templates = { BLOCK.CMD : BASE_TYPE.ASYN_TIMEOUT,   BLOCK.PARAM : BASE_TYPE.ASYN_TIMEOUT,   BLOCK.STATUS : "" }
        return link_extra_templates[self.block_type()]



class BITS(object):
    active_bits = None

    def __init__(self, block):
        assert isinstance(block,    BLOCK),   func_param_msg("block", "BLOCK")

        BITS.end()

        self._num_bits     = 0
        self._var_type     = "UINT16"
        self._started      = True
        self._block        = block
        self._offset       = -1
        BITS.active_bits   = self


    @staticmethod
    def get_bit_def(block):
        assert isinstance(block, BLOCK),      func_param_msg("block", "BLOCK")

        if BITS.active_bits is None:
            return BITS(block)

        if not block.optimize():
            max_num_bits = 16
        else:
            if BITS.active_bits._block.length() % 2:
                max_num_bits = 8
            else:
                max_num_bits = 16

        if BITS.active_bits._num_bits >= max_num_bits:
            excess_bits = BITS.active_bits._num_bits - max_num_bits
            bits = BITS(block)
            if excess_bits > 0:
                bits.add_bit(excess_bits)
            return bits

        return BITS.active_bits


    def add_bit(self, num):
        assert isinstance(num, int), func_param_msg("num", "integer")

        if not self._started:
            raise IfDefInternalError("BIT is undefined!")
        if num < 0:
            raise IfDefSyntaxError("Number of bits to skip must be greater than zero!")

        self._num_bits += num


    def var_type(self):
        return self._var_type


    def compute_offset(self, byte):
        self._block.compute_offset(byte)


    def calc_mask(self, bit):
        return '0x{:04X}'.format(1 << bit.bit_number())


    def link_extra(self, bit):
        if self._block.is_status_block():
            return " B={bit_num}".format(bit_num = bit.bit_number())
        elif self._block.is_cmd_block() or self._block.is_param_block():
            template = "{mask}, " + BASE_TYPE.ASYN_TIMEOUT
            return template.format(mask = self.calc_mask(bit))
        else:
            raise IfDefInternalError("Unknown db type: " + self._block.type())


    @staticmethod
    def end(next_var_width = None):
        if BITS.active_bits is None:
            return

        self = BITS.active_bits
        if self._started == False:
            return

        if self._block.optimize() and self._num_bits <= 8 and next_var_width is not None and next_var_width == 1:
            self._var_type = "UINT8"

        byte_width   = _bytes_in_type(self.var_type())
        self._offset = self._block.offset_for(byte_width)

        self.compute_offset(byte_width)
        self._started    = False
        BITS.active_bits = None



class BIT(BASE_TYPE):
    pv_types    = { BLOCK.CMD : "bo",   BLOCK.PARAM : "bo",   BLOCK.STATUS : "bi" }
    var_types   = { BLOCK.CMD : "",     BLOCK.PARAM : "",     BLOCK.STATUS : "WORD" }

    @staticmethod
    def skip(bit_def, num):
        bit_def.add_bit(num)


    def __init__(self, source, bit_def, name, keyword_params):
        assert isinstance(bit_def, BITS), func_param_msg("bit_def", "BITS")

        self._bit_def  = bit_def
        self._bit_num  = bit_def._num_bits

        #
        # BASE_TYPE.__init__ must be after self initialization
        #
        # 'WORD' is used as a placeholder only
        BASE_TYPE.__init__(self, source, bit_def._block, name, "WORD", keyword_params)


    def _end_bits(self):
        pass


    def pv_type(self):
        return BIT.pv_types[self.block_type()]


    def plc_type(self):
        return "BOOL"


    def offset(self):
        return self._bit_def._offset + self._param_offset


    def bit_number(self):
        return self._bit_num


    def compute_offset(self):
        self._bit_def.add_bit(1)


    def pv_template(self, test = False):
        return self._block.pv_template(test = test, asyntype = "asynUInt32Digital", asynio = "asynMask")


    def link_extra(self):
        return self._bit_def.link_extra(self)


    def var_type(self):
        if self.is_command() or self.is_parameter():
            return ""
        return self._bit_def.var_type()



class ALARM(BIT):
    def __init__(self, source, bit_def, name, severity, message, keyword_params):
        BIT.__init__(self, source, bit_def, name, keyword_params)

        self._severity = severity
        self._message  = message
        self._archive  = keyword_params.get("ARCHIVE", False)
        if not isinstance(self._archive, bool):
            self._archive = True


    def archive(self):
        return self._archive


    def message(self):
        return self._message



class ANALOG(BASE_TYPE):
    pv_types = { BLOCK.CMD : "ao",   BLOCK.PARAM : "ao",   BLOCK.STATUS : "ai" }

    def __init__(self, source, block, name, plc_var_type, keyword_params):
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_template(self, test = False):
        if self._var_type in self._block.valid_type_pairs()["REAL"]:
            return BASE_TYPE.pv_template(self, test = test, asyntype = "asynFloat64")
        return BASE_TYPE.pv_template(self, test = test)


    def pv_type(self):
        return ANALOG.pv_types[self.block_type()]



class ENUM(BASE_TYPE):
    pv_types = { BLOCK.CMD : "mbbo",   BLOCK.PARAM : "mbbo",   BLOCK.STATUS : "mbbi" }

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        _test_and_set_pv(keyword_params, "NOBT", nobt)
        _test_and_set_pv(keyword_params, "SHFT", shift)
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_type(self):
        return ENUM.pv_types[self.block_type()]



class BITMASK(BASE_TYPE):
    pv_types = { BLOCK.CMD : "mbboDirect",   BLOCK.PARAM : "mbboDirect",   BLOCK.STATUS : "mbbiDirect" }

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        _test_and_set_pv(keyword_params, "NOBT", nobt)
        _test_and_set_pv(keyword_params, "SHFT", shift)
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_type(self):
        return BITMASK.pv_types[self.block_type()]


    def pv_template(self, test = False):
        return self._block.pv_template(test = test, asyntype = "asynUInt32Digital", asynio = "asynMask")


    def link_extra(self):
        if self.is_status():
            return ""
        elif self.is_command() or self.is_parameter():
            return "0xFFFF, " + BASE_TYPE.ASYN_TIMEOUT
        else:
            raise IfDefInternalError("Unknown db type: " + self.block_type())





#
# Internal functions
#

def func_param_msg(param, ptype, atype = None):
    if atype is None:
        return "'{param}' must be of type {type}!".format(param = param, type = ptype)
    return "'{param}' must be of type {type} (not it is {atype})!".format(param = param, type = ptype, atype = atype)


def _test_and_set(keyword_params, key, value):
    if key not in keyword_params:
       keyword_params[key] = str(value)


def _test_and_set_pv(keyword_params, key, value):
    _test_and_set(keyword_params, BASE_TYPE.PV_PREFIX + key, value)


def _bits_in_type(var_type):
    try:
        return bits_in_type_map[var_type]
    except KeyError:
        raise IfDefSyntaxError("Unknown type: " + var_type)


def _bytes_in_type(var_type):
    assert isinstance(var_type, str)

    return _bits_in_type(var_type) // 8


"""
"""


if __name__ == "__main__":
    pass
