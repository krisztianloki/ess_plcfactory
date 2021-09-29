# vim: set fileencoding=utf-8 :
from __future__ import absolute_import
from __future__ import print_function

import os
import shutil
import tempfile
import unittest

import helpers


class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.dirpath)



class TestHelpers(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_makedirs(self):
        with mkdtemp() as rootdir:
            # Test single directory
            p1 = os.path.join(rootdir, "adir")
            helpers.makedirs(p1)
            self.assertTrue(os.path.isdir(p1))

            # Test already existing directory
            helpers.makedirs(p1)

            # Test multilevel directory path
            p2 = os.path.join(rootdir, "bdir", "many", "levels", "deep")
            helpers.makedirs(p2)
            self.assertTrue(os.path.isdir(p2))

            # Test already existing directory
            helpers.makedirs(p2)


    def test_sanitizeFilename(self):
        invalid_format = "this-has-a-{}-here"
        invalid_chars = '<>:"/\|?*'
        for i in invalid_chars:
            self.assertEqual(helpers.sanitizeFilename(invalid_format.format(i)), invalid_format.format('_'))

        # Test accented chars
        self.assertEqual(helpers.sanitizeFilename("Krisztián"), "Krisztian")

        # Test that path separator is replaced
        self.assertEqual(helpers.sanitizeFilename(os.path.join("this-path", invalid_format.format(""))), "this-path_{}".format(invalid_format.format("")))


    def test_sanitize_path(self):
        invalid_format = os.path.join("this-{i}-path", "has-a-{i}-here")
        invalid_chars = '<>:"\|?*'
        for i in invalid_chars:
            self.assertEqual(helpers.sanitize_path(invalid_format.format(i = i)), invalid_format.format(i = '_'))

        # Test accented chars
        self.assertEqual(helpers.sanitize_path("Krisztián:"), "Krisztian_")

        # Test that path separator is NOT replaced
        self.assertEqual(helpers.sanitize_path(os.path.join("another-path", invalid_format.format(i = "B"))), os.path.join("another-path", invalid_format.format(i = "B")))


    def test_url_strip_user(self):
        url = "https://{}gitlab.esss.lu.se:99/icshwi/plcfactory?name=foo#frag"
        self.assertEqual(helpers.url_strip_user(url.format("")), url.format(""))

        self.assertEqual(helpers.url_strip_user(url.format("krisztianloki@")), url.format(""))


    def test_url_to_path(self):
        path = "master/blob/test_helpers.py"
        urlbase = "gitlab.esss.lu.se/icshwi/plcfactory/"
        url = "https://{{usr}}{}{{path}}".format(urlbase)
        self.assertEqual(helpers.url_to_path(url.format(usr = "", path = path)), os.path.join(urlbase, path))

        self.assertEqual(helpers.url_to_path(url.format(usr = "krisztianloki@", path = path)), os.path.join(urlbase, path))


    def test_url_to_host(self):
        url = "https://gitlab.esss.lu.se/icshwi/plcfactory"
        self.assertEqual(helpers.url_to_host(url), "gitlab.esss.lu.se")

        url = "https://krisztianloki@gitlab.esss.lu.se/icshwi/plcfactory"
        self.assertEqual(helpers.url_to_host(url), "gitlab.esss.lu.se")


    def test_urljoin(self):
        base = "https://ccdb.esss.lu.se"
        rest = "rest"
        self.assertEqual(helpers.urljoin(base, rest), "{}/{}".format(base, rest))
        self.assertEqual(helpers.urljoin(base + "/", rest), "{}/{}".format(base, rest))
        self.assertEqual(helpers.urljoin(base, "/" + rest), "{}/{}".format(base, rest))
        self.assertEqual(helpers.urljoin(base, "/", rest, "/v1"), "{}/{}/v1".format(base, rest))

        endpoint = "slotNames"
        self.assertEqual(helpers.urljoin(base, rest, endpoint), "{}/{}/{}".format(base, rest, endpoint))
        endpoint = "slotNames?name=huha"
        self.assertEqual(helpers.urljoin(base, rest, endpoint), "{}/{}/{}".format(base, rest, endpoint))
        endpoint = "slotNames/?name=huha"
        self.assertEqual(helpers.urljoin(base, rest, endpoint), "{}/{}/{}".format(base, rest, endpoint))

        # Should work without a base too
        self.assertEqual(helpers.urljoin(rest, endpoint), "{}/{}".format(rest, endpoint))


    def test_sanitize_url(self):
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se"), "https://gitlab.esss.lu.se")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se/"), "https://gitlab.esss.lu.se/")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se/ioc"), "https://gitlab.esss.lu.se/ioc")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se/ioc/"), "https://gitlab.esss.lu.se/ioc/")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se//ioc"), "https://gitlab.esss.lu.se/ioc")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se///ioc"), "https://gitlab.esss.lu.se/ioc")
        self.assertEqual(helpers.sanitize_url("https://gitlab.esss.lu.se////ioc"), "https://gitlab.esss.lu.se/ioc")


    def test_tounicode(self):
        import sys
        string = "this-is-a-string"
        string2 = "this-is-á-string"
        uni = u"this-is-á-unicode-string"
        if sys.version_info.major == 2:
            # Test ASCII string
            cstring = helpers.tounicode(string)
            self.assertIsInstance(cstring, unicode)
            self.assertEqual(cstring, string)
            # Test utf-8 string
            cstring2 = helpers.tounicode(string2)
            self.assertIsInstance(cstring2, unicode)
            self.assertEqual(cstring2, string2.decode("utf-8"))
            # Test unicode string
            cuni = helpers.tounicode(uni)
            self.assertIsInstance(cuni, unicode)
            self.assertEqual(cuni, uni)
        else:
            cstring = helpers.tounicode(string)
            self.assertIsInstance(cstring, str)
            self.assertEqual(cstring, string)
            cstring2 = helpers.tounicode(string2)
            self.assertIsInstance(cstring2, str)
            self.assertEqual(cstring2, string2)
            cuni = helpers.tounicode(uni)
            self.assertIsInstance(cuni, str)
            self.assertEqual(cuni, uni)


    def test_Path(self):
        try:
            fp = helpers.FakePath(os.path.join("this", "is", "a", "path")).parts
        except AttributeError:
            return
        p = helpers.Path(os.path.join("this", "is", "a", "path")).parts
        self.assertEqual(p, fp)



if __name__ == "__main__":
    unittest.main()
