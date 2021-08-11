from __future__ import absolute_import
from __future__ import print_function


import collections
import os
import shutil
import tempfile
import unittest

import tf_ifdef


class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        if type is None:
            shutil.rmtree(self.dirpath)


class TestIF_DEF(unittest.TestCase):
    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_pv_name(self):
        with mkdtemp(prefix = "test-ifdef-pvname") as tmpdir:
            pv_name_def = os.path.join(tmpdir, "pvname.def")
            with open(pv_name_def, "w") as def_file:
                print("""
define_status_block()

add_digital("both")
add_digital("plc", PV_NAME="epics")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(pv_name_def, QUIET = True)

            var = ifdef.has_pv("both")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "both")
            self.assertEqual(var.name(), "both")
            self.assertEqual(var.fqpn(), "INST:SLOT:both")
            self.assertEqual(len(var._pv_fields), 0)

            var = ifdef.has_pv("plc")
            self.assertIsNone(var)

            var = ifdef.has_pv("epics")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "epics")
            self.assertEqual(var.name(), "plc")
            self.assertEqual(var.fqpn(), "INST:SLOT:epics")
            self.assertEqual(len(var._pv_fields), 0)

            with self.assertRaises(tf_ifdef.IfDefInternalError):
                tf_ifdef.PV.create_fqpn("foo")

            with self.assertRaises(tf_ifdef.IfDefInternalError):
                tf_ifdef.PV.create_root_fqpn("foo")

            ifdef = tf_ifdef.IF_DEF(QUIET = True)

            ifdef.define_status_block()
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                ifdef.add_digital("foo", PV_NAME="bar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
            bar = ifdef.add_digital("foo", PV_NAME="$(bar)-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")._var
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                bar.fqpn("foobar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                bar.fqpn("foobar-and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write.DESC")
            bar.fqpn("foobar.and-then-some-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")


    def test_alias(self):
        with mkdtemp(prefix = "test-ifdef-alias") as tmpdir:
            alias_def = os.path.join(tmpdir, "alias.def")
            with open(alias_def, "w") as def_file:
                print("""
define_status_block()

add_digital("no-alias")
add_digital("foo", PV_ALIAS="bar")
add_digital("foo2", PV_ALIAS=["bar2", "foobar2"])
add_digital("short", PV_ALIAS="an-alias-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alias_def, QUIET = True)

            var = ifdef.has_pv("no-alias")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "no-alias")
            self.assertEqual(var.fqpn(), "INST:SLOT:no-alias")
            self.assertEqual(var.name(), "no-alias")
            self.assertEqual(var._pv_aliases, [])
            self.assertEqual(var.build_pv_alias(), "")

            var = ifdef.has_pv("foo")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "foo")
            self.assertEqual(var.fqpn(), "INST:SLOT:foo")
            self.assertEqual(var.name(), "foo")
            self.assertEqual(var._pv_aliases, ["bar"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar")
""")

            var = ifdef.has_pv("foo2")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "foo2")
            self.assertEqual(var.fqpn(), "INST:SLOT:foo2")
            self.assertEqual(var.name(), "foo2")
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
""")
            var.add_alias("plus")
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2", "plus"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
\talias("INST:SLOT:plus")
""")
            var.add_alias(["left", "right"])
            self.assertEqual(var._pv_aliases, ["bar2", "foobar2", "plus", "left", "right"])
            self.assertEqual(var.build_pv_alias(), """
\talias("INST:SLOT:bar2")
\talias("INST:SLOT:foobar2")
\talias("INST:SLOT:plus")
\talias("INST:SLOT:left")
\talias("INST:SLOT:right")
""")

            var = ifdef.has_pv("short")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "short")
            self.assertEqual(var.fqpn(), "INST:SLOT:short")
            self.assertEqual(var.name(), "short")
            self.assertEqual(var._pv_aliases, ["an-alias-that-is-a-lot-longer-than-permitted-because-I-had-so-much-to-write"])
            self.assertGreater(len(var._pv_aliases[0]), 60)
            with self.assertRaises(tf_ifdef.PVNameLengthException):
                var.build_pv_alias()


    def test_fields(self):
        with mkdtemp(prefix = "test-ifdef-fields") as tmpdir:
            field_def = os.path.join(tmpdir, "field.def")
            with open(field_def, "w") as def_file:
                print("""
define_status_block()

add_digital("no-field")
add_digital("desc", PV_DESC="description")
add_digital("long-desc", PV_DESC="this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be")
add_digital("moar-fields", PV_DESC="desc", PV_HIGH="0")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(field_def, QUIET = True)

            var = ifdef.has_pv("no-field")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "no-field")
            self.assertEqual(len(var._pv_fields), 0)
            self.assertNotIsInstance(var._pv_fields, collections.OrderedDict)
            self.assertEqual(var.build_pv_extra(), "")

            var = ifdef.has_pv("desc")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "desc")
            self.assertEqual(var.get_pv_field("DESC"), "description")
            self.assertEqual(var.get_pv_field(tf_ifdef.PV.PV_DESC), "description")
            self.assertEqual(len(var._pv_fields), 1)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "description")""")

            var = ifdef.has_pv("long-desc")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(var.pv_name(), "long-desc")
            self.assertGreater(len(var.get_parameter(tf_ifdef.PV.PV_DESC)), 40)
            self.assertEqual(len(var.get_pv_field("DESC")), 40)
            self.assertEqual(var.get_pv_field("DESC"), "this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be"[:40])
            self.assertEqual(len(var._pv_fields), 1)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "{}")""".format("this-description-is-a-lot-longer-than-permitted-because-I-want-it-to-be"[:40]))

            var = ifdef.has_pv("moar-fields")
            self.assertIsInstance(var, tf_ifdef.BIT)
            self.assertEqual(len(var._pv_fields), 2)
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "desc")
\tfield(HIGH, "0")""")
            var.set_pv_field("ZNA", "znam")
            self.assertEqual(len(var._pv_fields), 3)
            self.assertEqual(var.get_pv_field("ZNA"), "znam")
            var.set_pv_field(tf_ifdef.PV.PV_ONAM, "onam")
            self.assertEqual(len(var._pv_fields), 4)
            self.assertEqual(var.get_pv_field("ONAM"), "onam")
            self.assertEqual(var.build_pv_extra(), """
\tfield(DESC, "desc")
\tfield(HIGH, "0")
\tfield(ONAM, "onam")
\tfield(ZNA,  "znam")""")


    def test_add_alarm_limits(self):
        with mkdtemp(prefix = "test-ifdef-add-alarm-limits") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
add_minor_low_limit("milow")
add_major_low_limit("malow")
add_minor_high_limit("mihigh", "REAL")
add_major_high_limit("mahigh", "INT")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            meas = ifdef.has_pv("meas")
            self.assertIsInstance(meas, tf_ifdef.ANALOG)
            self.assertEqual(meas.plc_type(), "REAL")
            self.assertEqual(meas.get_pv_field("LSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("LLSV"), "MAJOR")
            self.assertEqual(meas.get_pv_field("HSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("HHSV"), "MAJOR")
            self.assertEqual(meas.build_pv_extra(), """
\tfield(HHSV, "MAJOR")
\tfield(HSV,  "MINOR")
\tfield(LLSV, "MAJOR")
\tfield(LSV,  "MINOR")""")

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            var = ifdef.has_pv("milow")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#milow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            check_common_limit(ivar)

            var = ifdef.has_pv("malow")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#malow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOLO")
            check_common_limit(ivar)

            var = ifdef.has_pv("mihigh")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "REAL")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#mihigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIGH")
            check_common_limit(ivar)

            var = ifdef.has_pv("mahigh")
            self.assertIsInstance(var, tf_ifdef.ANALOG)
            self.assertEqual(var.plc_type(), "INT")
            self.assertFalse(var._pv_fields)

            ivar = ifdef.has_pv("#mahigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            check_common_limit(ivar)


    def test_set_alarm_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-alarm-limits-from") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
set_minor_low_limit_from("milow")
set_major_low_limit_from("malow", EXTERNAL_PV = True)
set_minor_high_limit_from("mihigh")
set_major_high_limit_from("ext:mahigh")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            meas = ifdef.has_pv("meas")
            self.assertIsInstance(meas, tf_ifdef.ANALOG)
            self.assertEqual(meas.plc_type(), "REAL")
            self.assertEqual(meas.get_pv_field("LSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("LLSV"), "MAJOR")
            self.assertEqual(meas.get_pv_field("HSV"), "MINOR")
            self.assertEqual(meas.get_pv_field("HHSV"), "MAJOR")
            self.assertEqual(meas.build_pv_extra(), """
\tfield(HHSV, "MAJOR")
\tfield(HSV,  "MINOR")
\tfield(LLSV, "MAJOR")
\tfield(LSV,  "MINOR")""")

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            ivar = ifdef.has_pv("#milow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:milow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#malow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "malow CP")
            self.assertEqual(ivar.get_parameter("PV_DOL"), "malow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.LOLO")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#mihigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:mihigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIGH")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#mahigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "ext:mahigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            check_common_limit(ivar)


    def test_set_multiple_alarm_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-multiple-alarm-limits-from") as tmpdir:
            alarm_def = os.path.join(tmpdir, "alarm.def")
            with open(alarm_def, "w") as def_file:
                print("""
define_status_block()

add_analog("meas", "REAL")
set_minor_low_limit_from("limit")
set_major_high_limit_from("limit2")

add_analog("meas2", "INT")
#set_minor_high_limit_from("")
set_major_high_limit_from("limit2")
set_major_low_limit_from("limit")

add_analog("meas3", "WORD")
set_minor_high_limit_from("limit")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(alarm_def, QUIET = True)

            def check_limited(name, typ, field, sevr, field_num):
                meas = ifdef.has_pv(name)
                self.assertIsInstance(meas, tf_ifdef.ANALOG)
                self.assertEqual(meas.plc_type(), typ)
                self.assertEqual(meas.get_pv_field(field), sevr)
                self.assertEqual(len(meas._pv_fields), field_num)

            check_limited("meas", "REAL", "LSV", "MINOR", 2)
            check_limited("meas", "REAL", "HHSV", "MAJOR", 2)
            check_limited("meas2", "INT", "LLSV", "MAJOR", 2)
            check_limited("meas2", "INT", "HHSV", "MAJOR", 2)
            check_limited("meas3", "WORD", "HSV", "MINOR", 1)

            limit = ifdef.has_pv("#limit")
            self.assertIsInstance(limit, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(limit.get_pv_field("DOL"), "INST:SLOT:limit CP")
            self.assertEqual(limit.get_pv_field("OMSL"), "closed_loop")
            self.assertEqual(limit.get_pv_field("OUTA"), "INST:SLOT:meas.LOW")
            self.assertEqual(limit.get_pv_field("OUTB"), "INST:SLOT:meas2.LOLO")
            self.assertEqual(limit.get_pv_field("OUTC"), "INST:SLOT:meas3.HIGH")
            self.assertTrue(limit.get_pv_field("DESC"))
            self.assertEqual(len(limit._pv_fields), 6)

            limit = ifdef.has_pv("#limit2")
            self.assertIsInstance(limit, tf_ifdef.ANALOG_ALARM_LIMIT)
            self.assertEqual(limit.get_pv_field("DOL"), "INST:SLOT:limit2 CP")
            self.assertEqual(limit.get_pv_field("OMSL"), "closed_loop")
            self.assertEqual(limit.get_pv_field("OUTA"), "INST:SLOT:meas.HIHI")
            self.assertEqual(limit.get_pv_field("OUTB"), "INST:SLOT:meas2.HIHI")
            self.assertTrue(limit.get_pv_field("DESC"))
            self.assertEqual(len(limit._pv_fields), 5)


    def test_set_drive_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-drive-limits-from") as tmpdir:
            drive_def = os.path.join(tmpdir, "drive.def")
            with open(drive_def, "w") as def_file:
                print("""
define_parameter_block()

add_analog("param", "REAL")
set_low_drive_limit_from("dlow")
set_high_drive_limit_from("ext:dhigh")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(drive_def, QUIET = True)

            param = ifdef.has_pv("param")
            self.assertIsInstance(param, tf_ifdef.ANALOG)
            self.assertEqual(param.plc_type(), "REAL")
            self.assertEqual(len(param._pv_fields), 0)

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 4)

            ivar = ifdef.has_pv("#dlow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:dlow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.LOPR")
            check_common_limit(ivar)

            ivar = ifdef.has_pv("#dhigh")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "ext:dhigh CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.HOPR")
            check_common_limit(ivar)


    def test_set_multiple_drive_limits_from(self):
        with mkdtemp(prefix = "test-ifdef-set-multiple-drive-limits-from") as tmpdir:
            drive_def = os.path.join(tmpdir, "drive.def")
            with open(drive_def, "w") as def_file:
                print("""
define_parameter_block()

add_analog("param", "REAL")
set_low_drive_limit_from("dlow")

add_analog("param1", "INT")
set_low_drive_limit_from("dlow")

add_analog("param2", "WORD")
set_high_drive_limit_from("dlow")
""", file = def_file)

            ifdef = tf_ifdef.IF_DEF.parse(drive_def, QUIET = True)

            def check_driven(var, typ, limits):
                self.assertIsInstance(var, tf_ifdef.ANALOG)
                self.assertEqual(var.plc_type(), typ)
                if limits:
                    self.assertEqual(set(var._pv_fields.keys()), set(["PV_DRVL", "PV_DRVH", "PV_LOPR", "PV_HOPR"]))
                else:
                    self.assertEqual(len(var._pv_fields), 0)

            param = ifdef.has_pv("param")
            check_driven(param, "REAL", False)

            param = ifdef.has_pv("param1")
            check_driven(param, "INT", True)

            param = ifdef.has_pv("param2")
            check_driven(param, "WORD", True)

            def check_common_limit(var):
                self.assertEqual(var.get_pv_field("OMSL"), "closed_loop")
                self.assertTrue(var.get_pv_field("DESC"))
                self.assertEqual(len(var._pv_fields), 6)

            ivar = ifdef.has_pv("#dlow")
            self.assertIsInstance(ivar, tf_ifdef.ANALOG_DRIVE_LIMIT)
            self.assertEqual(ivar.get_pv_field("DOL"), "INST:SLOT:dlow CP")
            self.assertEqual(ivar.get_pv_field("OUTA"), "INST:SLOT:param.LOPR")
            self.assertEqual(ivar.get_pv_field("OUTB"), "INST:SLOT:param1.LOPR")
            self.assertEqual(ivar.get_pv_field("OUTC"), "INST:SLOT:param2.HOPR")
            check_common_limit(ivar)



if __name__ == "__main__":
    unittest.main()

