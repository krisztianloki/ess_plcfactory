import unittest
import plcf
import plcf_glob

class FakeDevice(object):
    def name(self):
        return "FakeDevice"


    def description(self):
        return "FakeDescription"


    def deviceType(self):
        return "FakeDeviceType"


    def propertiesDict(self):
        return { "infinity"  : "infinity",
                 "lonG"      : "lonG", "lonGer": "lonGer", "lengthy": "lonG",
                 "short"     : "shorter", "shorter" : "tiny",
                 "template"  : "beast-template",
                 "forty-two" : "42",
                 "A"         : "AB", "AB": "AC"}


    def backtrack(self, prop):
        if prop == "EPICSToPLCDataBlockStartOffset":
            return str(42)
        return prop



class TestPLCF(unittest.TestCase):
    def setUp(self):
        plcf_glob.root_installation_slot = "root_slot"
        self.device = FakeDevice()
        self.cplcf  = plcf.PLCF(self.device)


    def tearDown(self):
        pass


    def testEmptyPLCF(self):
        line = "[PLCF#]"
        self.assertEqual(self.cplcf.processLine(line), "")


    def testUnclosedPLCF(self):
        line = "[PLCF#"
        with self.assertRaises(plcf.PLCFException):
            self.cplcf.processLine(line)


    def testSquareBracketInPLCF(self):
        line = "[PLCF#[]"
        with self.assertRaises(plcf.PLCFException):
            self.cplcf.processLine(line)


    def testParenInPLCF(self):
        line = "[PLCF#(]"
        with self.assertRaises(AssertionError):
            self.cplcf.processLine(line)


#    noException("[PLCF#^(this is (a) weird property)]")

    def testParenPropertyInPLCF(self):
        line = "[PLCF#(property]"
        with self.assertRaises(AssertionError):
            self.cplcf.processLine(line)


    def testParenExtInPLCF(self):
        line = "[PLCF#ext.(]"
        with self.assertRaises(AssertionError):
            self.cplcf.processLine(line)


    def testUnclosedParenExtInPLCF(self):
        line = "[PLCF#ext.fn(()]"
        with self.assertRaises(AssertionError):
            self.cplcf.processLine(line)


    def testNoSuchPropertyInPLCF(self):
        prop = "infinity"
        line = "[PLCF#{}]".format(prop)
        self.assertEqual(self.cplcf.processLine(line), prop)


#    match("[PLCF#lengthyer]", "lonGer")

#    match("[PLCF#lengthyer lengthy]", "lonGer lonG")

    def testPropertyInPLCF(self):
        line   = "[PLCF#short]"
        result = "tiny"
        self.assertEqual(self.cplcf.processLine(line), result)
        line   = "[PLCF#forty-two]"
        result = "42"
        self.assertEqual(self.cplcf.processLine(line), result)


    def testMultiplePropertyAppearanceInPLCF(self):
        line   = "[PLCF#template template short]"
        result = "beast-template beast-template tiny"
        self.assertEqual(self.cplcf.processLine(line), result)


#    def testRecursivePropertySubst(self):
#        line   = "[PLCF#A]"
#        result = self.device.propertiesDict()["A"]
#        self.assertEqual(self.cplcf.processLine(line), result)


    def testCounterInPLCF(self):
        counter  = "Counter1"
        expr     = "{}".format(counter)
        line     = "[PLCF#{}]".format(expr)
        self.assertTrue(plcf.PLCF.hasCounter(expr))
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF.wordIndex(expr, counter), 0)
        self.assertEqual(plcf.PLCF.wordIndex(line, counter), 6)

        counterline = "#COUNTER {} = {}"
        const = 42
        lines = [counterline.format(counter, "[PLCF#{}]".format(const)), line]
        (plines, pcounters) = plcf.PLCF.evalCounters(lines)
        icounters = plcf.PLCF.initializeCounters()
        icounters[counter] = const
        self.assertEqual(pcounters, icounters)
        self.assertEqual(plines, [counterline.format(counter, const), str(const)])

        counter  = "Counter1-2"
        expr     = "{}".format(counter)
        line     = "[PLCF#{}]".format(expr)
        self.assertTrue(plcf.PLCF.hasCounter(expr))
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF.wordIndex(expr, counter), 0)
        self.assertEqual(plcf.PLCF.wordIndex(line, counter), 6)

        counter  = "Counter1"
        counter2 = "Counter2"
        expr     = "{} + {}".format(counter, counter2)
        line     = "[PLCF#{}]".format(expr)
        self.assertTrue(plcf.PLCF.hasCounter(expr))
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF.wordIndex(expr, counter), 0)
        self.assertEqual(plcf.PLCF.wordIndex(line, counter), 6)
        self.assertEqual(plcf.PLCF.wordIndex(expr, counter2), 11)
        self.assertEqual(plcf.PLCF.wordIndex(line, counter2), 17)
        counters = plcf.PLCF.initializeCounters()
        counters[counter]  = 42
        counters[counter2] = 24
        self.assertEqual(plcf.PLCF._evalCounter(line, counters), str(counters[counter] + counters[counter2]))

        const    = 42
        expr     = "{} + {}".format(const, counter)
        line     = "[PLCF#{}]".format(expr)
        counters = plcf.PLCF.initializeCounters()
        counters[counter] = 42
        self.assertTrue(plcf.PLCF.hasCounter(expr))
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, counters), str(const + counters[counter]))

        const    = "forty-two"
        expr     = "{} + {}".format(const, counter)
        line     = "[PLCF#{}]".format(expr)
        counters = plcf.PLCF.initializeCounters()
        counters[counter] = 42
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(self.cplcf.processLine(line), "[PLCF#42 + {}]".format(counter))
        line = self.cplcf.processLine(line)
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, counters), str(42 + counters[counter]))



    def testBacktrackInPLCF(self):
        expr = "^(EPICSToPLCDataBlockStartOffset)"
        line = "[PLCF#{}]".format(expr)
        self.assertEqual(self.cplcf.processLine(line), "42")


    def testBacktrackAndCounterInPLCF(self):
        backtrack = "^(EPICSToPLCDataBlockStartOffset)"
        counter   = "Counter1"
        line      = "[PLCF#{} + {}]".format(backtrack, counter)
        counters = plcf.PLCF.initializeCounters()
        counters[counter] = 42
        self.assertTrue(plcf.PLCF.hasCounter(line))
        self.assertEqual(self.cplcf.processLine(line), "[PLCF#{} + {}]".format(42, counter))


    def testNoCounterInPLCF(self):
        expr = "Counter42"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        with self.assertRaises(ValueError):
            plcf.PLCF.wordIndex(line, "Counter4")
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        expr = "Counter1Cmd"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        expr = "CounterCmd"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        expr = "Counter"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        expr = "CmdCounter1"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        expr = "CmdCounter"
        line = "[PLCF#{}]".format(expr)
        self.assertFalse(plcf.PLCF.hasCounter(expr))
        self.assertFalse(plcf.PLCF.hasCounter(line))
        self.assertEqual(plcf.PLCF._evalCounter(line, plcf.PLCF.initializeCounters()), expr)

        counter = "CounterCmd"
        counterline = "#COUNTER {} = {}"
        const = 42
        lines = [counterline.format(counter, "[PLCF#{}]".format(const)), line]
        with self.assertRaises(AssertionError):
            plcf.PLCF.evalCounters(lines)


    def testCounterAndNoCounterInPLCF(self):
        not_counter  = "Counter1Cmd"
        real_counter = "Counter1"
        expr = "{} {}".format(not_counter, real_counter)
        line = "[PLCF#{}]".format(expr)
        self.assertTrue(plcf.PLCF.hasCounter(line))

        counters = plcf.PLCF.initializeCounters()
        counters[real_counter] = 42
        self.assertEqual(plcf.PLCF._evalCounter(line, counters), "{} {}".format(not_counter, counters[real_counter]))


    def testSubstituteWord(self):
        word = "word"
        line = "This is word"
        self.assertEqual(plcf.PLCF.substituteWord(line, word, "Sparta")[0], "This is Sparta")

        word = "word"
        line = "This is myword"
        with self.assertRaises(ValueError):
            plcf.PLCF.substituteWord(line, word, "Sparta")



if __name__ == "__main__":
    unittest.main()
