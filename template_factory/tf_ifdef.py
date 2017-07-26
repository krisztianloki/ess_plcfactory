""" Template Factory: Interface Definition Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


import copy
#import inspect
import hashlib



inpv_template  = """record({recordtype}, "[PLCF#INSTALLATION_SLOT]:{name}")
{{{alias}
	field(SCAN, "I/O Intr")
	field(DTYP, "S7plc")
	field(INP,  "@$(PLCNAME)/{offset} T={var_type}{link_extra}"){pv_extra}
}}

"""


outpv_template = """record({{recordtype}}, "[PLCF#INSTALLATION_SLOT]:{{name}}")
{{{{{{alias}}
	field(DTYP, "{asyntype}")
	field(OUT,  "@{asynio}($(PLCNAME)write, {{offset}}, {{link_extra}}){{var_type}}"){{pv_extra}}
}}}}

"""




PV_PREFIX    = "PV_"
PV_ALIAS     = PV_PREFIX + "ALIAS"
STATUS       = "STATUS"
CMD          = "COMMAND"
PARAM        = "PARAMETER"
ASYN_TIMEOUT = "100"


PLC_types = {'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'SSTIME', 'TIME', 'DATE', 'TIME_OF_DAY', 'CHAR' }


bits_in_type_map = { 'UINT8'   : 8,  'INT8'   : 8,  'UNSIGN8' : 8,  'BYTE'       : 8,  'CHAR'       : 8,
                     'UINT16'  : 16, 'INT16'  : 16, 'SHORT'   : 16, 'UNSIGN16'   : 16, 'WORD'       : 16, 'INT16SM'  : 16, 'BCD_UNSIGNED' : 16, 'BCD_SIGNED' : 16, 'INT' : 16,
                     'UINT32'  : 32, 'INT32'  : 32, 'LONG'    : 32, 'UNSIGN32'   : 32, 'DWORD'      : 32, 'INT32_LE' : 32, 'INT32_BE'     : 32, 'DINT' : 32,
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
        assert isinstance(source,  str),  func_param_msg("source",  "string")
        assert isinstance(comment, bool), func_param_msg("comment", "bool")

        self._source  = source
        self._comment = comment


    @staticmethod
    def fromline(source):
        return "<<<--- " + str(source).lstrip()


    def source(self):
        return self._source



class VERBATIM(SOURCE):
    def __init__(self, verbatim):
        assert isinstance(verbatim, str),  func_param_msg("verbatim", "string")

        SOURCE.__init__(self, SOURCE.fromline("add_verbatim()\n"))

        self._verbatim = verbatim


    def __str__(self):
        return self._verbatim



#
# Blocks
#
class BLOCK(SOURCE):
    def __init__(self, source, block_type):
        SOURCE.__init__(self, SOURCE.fromline(source))

        BITS.end()

        assert isinstance(block_type,    str)
        self._block_type    = block_type

        self._block_offset = 0
        self._length       = 0


    def _is_alignment_needed(self, width):
        # MODBUS cannot address the individual bytes in a WORD
        return (self.is_cmd_block() or self.is_param_block() or width > 1) and (self._block_offset % 2) == 1


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


    def valid_var_types(self):
        types = []
        for k,v in self.valid_type_pairs().iteritems():
            types += v
        return types


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

        for key, value in keyword_params.iteritems():
            if key.startswith(PV_PREFIX) or not key in PLC_types:
                continue

            if not value in self.valid_var_types():
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


    def pv_template(self, asyntype = None, asynio = None):
        pv_templates = { CMD : outpv_template,   PARAM : outpv_template,   STATUS : inpv_template }
        pv_temp = pv_templates[self.type()]

        if pv_temp is outpv_template:
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
        return dict(BYTE  = [ "UINT8",   "INT8",    "UNSIGN8", "BYTE", "CHAR" ],
                    WORD  = [ "UINT16",  "UNSIGN16", "WORD" ],
                    INT   = [ "INT16",   "SHORT" ],
                    DWORD = [ "UINT32",  "UNSIGN32", "DWORD" ],
                    DINT  = [ "INT32",   "LONG" ],
                    REAL  = [ "FLOAT32", "REAL32",   "FLOAT" ])


    def __init__(self, source):
        BLOCK.__init__(self, source, STATUS)


    def link_offset(self, var):
        offset_template = "[PLCF# ( {root} + {counter} ) * 2 + {offset}]"
        return offset_template.format(root = self.root_of_db(), counter = self.counter_keyword(), offset = var.offset())



#
# Special class to handle the similarities between CMD_BLOCK and PARAM_BLOCK
#
class MODBUS(object):
    @staticmethod
    def counter_keyword():
        return "Counter1"


    @staticmethod
    def root_of_db():
        return "^(EPICSToPLCDataBlockStartOffset)"


    @staticmethod
    def valid_type_pairs():
        return dict(BYTE  = [ "UINT16" ],
                    WORD  = [ "UINT16",     "BCD_UNSIGNED" ],
                    INT   = [ "INT16",      "BCD_SIGNED",  "INT16SM" ],
                    DWORD = [ "INT32_BE",   "INT32_LE" ],
                    DINT  = [ "INT32_BE",   "INT32_LE" ],
                    REAL  = [ "FLOAT32_BE", "FLOAT32_LE" ] )


    def link_offset(self, var):
        offset_template = "[PLCF# ( {root} + {counter} ) + {offset}]"
        return offset_template.format(root = self.root_of_db(), counter = self.counter_keyword(), offset = var.offset() // 2)




class CMD_BLOCK(MODBUS, BLOCK):
    @staticmethod
    def length_keyword():
        return "CommandWordsLength"


    def __init__(self, source):
        BLOCK.__init__(self, source, CMD)



class PARAM_BLOCK(MODBUS, BLOCK):
    @staticmethod
    def length_keyword():
        return "ParameterWordsLength"


    def __init__(self, source):
        BLOCK.__init__(self, source, PARAM)



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




class IF_DEF(object):
    def __init__(self, hashobj = None):
#        if hashobj is not None and not isinstance(hashobj, hashlib.HASH):
#            raise IfDefException("Expected a hash object from the hashlib module!")
        if hashobj is None:
            hashobj = DummyHash()

        BASE_TYPE.init()

        self._ifaces                = []
        self._STATUS                = None
        self._CMD                   = None
        self._PARAM                 = None
        self._active_BLOCK          = None
        self._overlap               = None
        self._active                = True
        self._source                = ""
        self._properties            = dict()
        self._to_plc_words_length   = 0
        self._from_plc_words_length = 0
        self._hash                  = hashobj

        self._properties[CMD_BLOCK.length_keyword()]    = 0
        self._properties[PARAM_BLOCK.length_keyword()]  = 0
        self._properties[STATUS_BLOCK.length_keyword()] = 0


    def _eval(self, source):
        self._source = source
        eval("self." + source.strip())


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
        if block is not None:
            block.end()
            self._properties[block.length_keyword()] = block.length() // 2
            print "{var}: {length}".format(var = block.length_keyword(), length = str(block.length() // 2))


    def _add(self, var):
        assert isinstance(var, SOURCE), func_param_msg("var", "SOURCE")

        self._ifaces.append(var)


    def _add_comment(self, line):
        assert isinstance(line, str), func_param_msg("line", "string")

        var   = SOURCE(line, True)
        self._add(var)


    def _add_source(self):
        self._add(SOURCE(SOURCE.fromline(self._source)))


    # returns the length of 'block' in (16 bit) words
    def _words_length_of(self, block):
        if block is None:
            return 0

        assert isinstance(block, BLOCK), func_param_msg("block", "BLOCK", type(block))

        return self._properties[block.length_keyword()]


    def _exception_if_active(self):
        if self._active:
            raise IfDefSyntaxError("The interface definition is still active!")


    def interfaces(self):
        self._exception_if_active()

        return self._ifaces


    def properties(self):
        self._exception_if_active()

        return self._properties


    def to_plc_words_length(self):
        self._exception_if_active()

        return self._to_plc_words_length


    def from_plc_words_length(self):
        self._exception_if_active()

        return self._from_plc_words_length


    def add(self, source):
        if not isinstance(source, str):
            raise IfDefSyntaxError("Interface definition lines must be strings!")

        if not self._active:
            raise IfDefSyntaxError("The interface definition is no longer active!")

        if source.startswith("_"):
            raise IfDefSyntaxError("Interface definition lines cannot start with '_'")

        if source.startswith("#TF#") or source.startswith("#-"):
            return

        if source.startswith("#"):
            self._add_comment(source[1:])
            return

        if source.strip() == "":
            self._add_comment(source)
            return

        self._hash.update(source)

        self._eval(source)


    def define_template(self, name, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Template name must be a string!")

        BASE_TYPE.add_template(name, keyword_params)
        self._add_source()


    def define_status_block(self):
        if self._STATUS is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._STATUS = STATUS_BLOCK(self._source)
        self._ifaces.append(self._STATUS)


    def define_command_block(self):
        if self._CMD is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._CMD = CMD_BLOCK(self._source)
        self._add(self._CMD)


    def define_parameter_block(self):
        if self._PARAM is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._PARAM = PARAM_BLOCK(self._source)
        self._add(self._PARAM)


    def define_overlap(self):
        if self._active_BLOCK is None:
            raise IfDefSyntaxError("Define block first")
        if self._overlap is not None:
            raise IfDefSyntaxError("End current overlap first")

        self._overlap = self._active_BLOCK.get_overlap()
        self._add_source()


    def end_overlap(self):
        if self._overlap is None:
            raise IfDefSyntaxError("No overlap found")

        self._overlap.end()
        self._overlap = None
        self._add_source()


    def add_bit(self, name = None, **keyword_params):
        self.add_digital(name, **keyword_params)


    def add_digital(self, name = None, **keyword_params):
        block = self._active_block()
        bit_def = self._active_bit_def()
        if name is None and "SKIP_BITS" not in keyword_params:
            keyword_params.update(SKIP_BITS = 1)
        var = BIT(self._source, bit_def, name, keyword_params)
        self._add(var)


    def skip_bit(self):
        self.skip_digital()


    def skip_digital(self):
        self.skip_digitals(1)


    def skip_bits(self, num):
        self.skip_digitals(num)


    def skip_digitals(self, num):
        if isinstance(num, str):
            num = int(num)

        if not isinstance(num, int):
            raise IfDefSyntaxError("Parameter must be a number!")

        self.add_bit(SKIP_BITS = num)


    def add_float(self, name, plc_var_type = "DINT", **keyword_params):
        self.add_analog(name, plc_var_type, **keyword_params)


    def add_analog(self, name, plc_var_type = "DINT", **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        block = self._active_block()
        var = ANALOG(self._source, block, name, plc_var_type, keyword_params)
        self._add(var)


    def add_enum(self, name, plc_var_type = "INT", nobt = 16, shift = 0, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        block = self._active_block()
        var = ENUM(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        self._add(var)


    def add_bitmask(self, name, plc_var_type = "INT", nobt = 16, shift = 0, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        block = self._active_block()
        var = BITMASK(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        self._add(var)


    def add_verbatim(self, verbatim):
        if not isinstance(verbatim, str):
            raise IfDefSyntaxError("Only strings can be copied verbatim!")

        var = VERBATIM(verbatim)
        self._add(var)


    def end_bits(self):
        self.end_digitals()


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
    templates = dict()


    @staticmethod
    def init():
        BASE_TYPE.templates = dict()


    def __init__(self, source, block, name, plc_var_type, keyword_params):
        SOURCE.__init__(self, SOURCE.fromline(source))

        assert isinstance(block,        BLOCK),                              func_param_msg("block",          "BLOCK")
        assert isinstance(name,         str),                                func_param_msg("name",           "string")
        assert isinstance(plc_var_type, str),                                func_param_msg("plc_var_type",   "string")
        assert keyword_params is None or isinstance(keyword_params, dict),   func_param_msg("keyword_params", "dict")

        self._end_bits()

        self._keyword_params = keyword_params
        self._expand_templates()

        """
           Check for PLC_TYPE="S7PLCTYPE|MODBUSTYPE"
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

        if isinstance(block, OVERLAP):
            self._overlapped = not block.is_empty()
        else:
            self._overlapped = False

        self._param_offset   = 0

        self.compute_offset()


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
        BITS.end()


    def name(self):
        """
           The name of the variable
        """
        return self._name


    def var_type(self):
        return self._var_type


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


    def is_valid(self):
        return True


    def _build_pv_extra(self):
        pv_field3 = "\tfield({key},  \"{value}\")\n"
        pv_field4 = "\tfield({key}, \"{value}\")\n"

        pv_extra_fields = "\n"
        for key in sorted(self._keyword_params.keys()):
            if key.startswith(PV_PREFIX) and key != PV_ALIAS:
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
        alias = "\n\talias(\"[PLCF#INSTALLATION_SLOT]:{alias}\")\n"
        if PV_ALIAS in self._keyword_params:
            return alias.format(alias = self._keyword_params[PV_ALIAS])

        return ""

    def toEPICS(self):
        return (self.source(),
                 self.pv_template().format(recordtype = self.pv_type(),
                                           name       = self.name(),
                                           alias      = self._build_pv_alias(),
                                           offset     = self.link_offset(),
                                           var_type   = self.var_type(),
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


    def pv_template(self, asyntype = "asynInt32", asynio = "asyn"):
        return self._block.pv_template(asyntype, asynio)


    def link_extra(self):
        link_extra_templates = { CMD : ASYN_TIMEOUT,   PARAM : ASYN_TIMEOUT,   STATUS : "" }
        return link_extra_templates[self.block_type()]



class BITS(object):
    active_bits = None

    def __init__(self, block):
        assert isinstance(block,    BLOCK),   func_param_msg("block", "BLOCK")

        BITS.end()

        self._num_bits     = 0
        self._started      = True
        self._block        = block
        self._offset       = -1
        BITS.active_bits   = self


    @staticmethod
    def get_bit_def(block):
        assert isinstance(block, BLOCK),      func_param_msg("block", "BLOCK")

        if BITS.active_bits is None:
            return BITS(block)

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
        if self._num_bits <= 8:
            return "UINT8"
        else:
            return "UINT16"


    def compute_offset(self, byte):
        self._block.compute_offset(byte)


    def calc_mask(self, bit):
        return '0x{:04X}'.format(1 << bit._bit_num)


    def link_extra(self, bit):
        if self._block.is_status_block():
            return " B={bit_num}".format(bit_num = bit._bit_num)
        elif self._block.is_cmd_block() or self._block.is_param_block():
            template = "{mask}, " + ASYN_TIMEOUT
            return template.format(mask = self.calc_mask(bit))
        else:
            raise IfDefInternalError("Unknown db type: " + self._block.type())


    @staticmethod
    def end():
        if BITS.active_bits is None:
            return

        self = BITS.active_bits
        if self._started == False:
            return

        byte_width   = _bytes_in_type(self.var_type())
        self._offset = self._block.offset_for(byte_width)

        self.compute_offset(byte_width)
        self._started    = False
        BITS.active_bits = None



class BIT(BASE_TYPE):
    pv_types  = { CMD : "bo",   PARAM : "bo",   STATUS : "bi" }
    var_types = { CMD : "",     PARAM : "",     STATUS : "WORD" }

    def __init__(self, source, bit_def, name, keyword_params):
        assert isinstance(bit_def, BITS), func_param_msg("bit_def", "BITS")

        if name is None:
            self._skip = True
            name       = "N/A"
        else:
            self._skip = False

        # 'WORD' is used as a placeholder only
        self._bit_def  = bit_def
        self._bit_num  = bit_def._num_bits

        #
        # BASE_TYPE.__init__ must be after self initialization
        #
        BASE_TYPE.__init__(self, source, bit_def._block, name, "WORD", keyword_params)


    def toEPICS(self):
        if self.is_valid():
            return BASE_TYPE.toEPICS(self)
        else:
            return (self.source(), "")


    def _end_bits(self):
        pass


    def pv_type(self):
        return BIT.pv_types[self.block_type()]


    def plc_type(self):
        return "BOOL"


    def offset(self):
        return self._bit_def._offset + self._param_offset


    def is_valid(self):
        return not self._skip


    def bit_number(self):
        return self._bit_num


    def compute_offset(self):
        num = 1
        if self._skip:
            num = self._keyword_params["SKIP_BITS"]
        self._bit_def.add_bit(num)


    def pv_template(self):
        return self._block.pv_template("asynUInt32Digital", "asynMask")


    def link_extra(self):
        return self._bit_def.link_extra(self)


    def var_type(self):
        if self.is_command() or self.is_parameter():
            return ""
        return self._bit_def.var_type()



class ANALOG(BASE_TYPE):
    pv_types = { CMD : "ao",   PARAM : "ao",   STATUS : "ai" }

    def __init__(self, source, block, name, plc_var_type, keyword_params):
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_template(self):
        if self._var_type in self._block.valid_type_pairs()["REAL"]:
            return BASE_TYPE.pv_template(self, "asynFloat64")
        return BASE_TYPE.pv_template(self)


    def pv_type(self):
        return ANALOG.pv_types[self.block_type()]



class ENUM(BASE_TYPE):
    pv_types = { CMD : "mbbo",   PARAM : "mbbo",   STATUS : "mbbi" }

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        _test_and_set_pv(keyword_params, "NOBT", nobt)
        _test_and_set_pv(keyword_params, "SHFT", shift)
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_type(self):
        return ENUM.pv_types[self.block_type()]



class BITMASK(BASE_TYPE):
    pv_types = { CMD : "mbboDirect",   PARAM : "mbboDirect",   STATUS : "mbbiDirect" }

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        _test_and_set_pv(keyword_params, "NOBT", nobt)
        _test_and_set_pv(keyword_params, "SHFT", shift)
        BASE_TYPE.__init__(self, source, block, name, plc_var_type, keyword_params)


    def pv_type(self):
        return BITMASK.pv_types[self.block_type()]


    def pv_template(self):
        return self._block.pv_template("asynUInt32Digital", "asynMask")


    def link_extra(self):
        if self.is_status():
            return ""
        elif self.is_command() or self.is_parameter():
            return "0xFFFF, " + ASYN_TIMEOUT
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
    _test_and_set(keyword_params, PV_PREFIX + key, value)


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
    bl = STATUS_BLOCK("foo")
    print bl.valid_var_types()
    bl = CMD_BLOCK("foo")
    print bl.valid_var_types()
    bl = PARAM_BLOCK("foo")
    print bl.valid_var_types()
