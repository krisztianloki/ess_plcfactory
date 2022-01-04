# vim: set fileencoding=utf-8 :
from __future__ import absolute_import
from __future__ import print_function

import os
import shutil
import tempfile
import unittest

import plcf_git


class mkdtemp(object):
    def __init__(self, **kwargs):
        self.dirpath = tempfile.mkdtemp(**kwargs)


    def __enter__(self):
        return self.dirpath


    def __exit__(self, type, value, traceback):
        if type is None:
            shutil.rmtree(self.dirpath)


class TestGIT(unittest.TestCase):
    EMPTY_REPO = "https://gitlab.esss.lu.se/krisztianloki/empty.git"
    TO_BE_INITIALIZED_REPO = "https://gitlab.esss.lu.se/krisztianloki/to-be-initialized.git"
    MULTIPLE_BRANCHES_REPO = "https://gitlab.esss.lu.se/krisztianloki/multiple-branches"


    def setUp(self):
        self.MULTIPLE_BRANCHES_REPO_GIT = self.MULTIPLE_BRANCHES_REPO + ".git"


    def test_clone_empty_repo(self):
        with mkdtemp(prefix = "test-plcf-git-empty-repo") as path:
            empty_repo = plcf_git.GIT.clone(self.EMPTY_REPO, path)
            self.assertEqual(empty_repo._url, self.EMPTY_REPO)
            self.assertEqual(empty_repo._default_branch, plcf_git.GIT.MASTER)
            self.assertEqual(empty_repo._branch, plcf_git.GIT.MASTER)

            # Try to clone it again, should just use the existing working copy
            empty_repo = plcf_git.GIT.clone(self.EMPTY_REPO, path)
            self.assertEqual(empty_repo._url, self.EMPTY_REPO)
            self.assertEqual(empty_repo._default_branch, plcf_git.GIT.MASTER)
            self.assertEqual(empty_repo._branch, plcf_git.GIT.MASTER)

            # Try to clone with explicit branch, should just use the existing working copy and checkout branch
            with self.assertRaises(plcf_git.GITException) as e:
                empty_repo = plcf_git.GIT.clone(self.EMPTY_REPO, path, branch = "main")
                self.assertEqual(e.exception.args[0], "Empty repository does not have branch 'main'")


    def test_clone_empty_repo_explicit_branch(self):
        with mkdtemp(prefix = "test-plcf-git-empty-repo-explicit-branch") as path:
            # Try to clone with explicit branch
            with self.assertRaises(plcf_git.GITException) as e:
                plcf_git.GIT.clone(self.EMPTY_REPO, path, branch = "main")
                self.assertEqual(e.exception.args[0], "Empty repository does not have branch 'main'")


    def test_initialize_empty_repo(self):
        with mkdtemp(prefix = "test-plcf-git-initialize-empty-repo") as path:
            initialized_repo = plcf_git.GIT.clone(self.TO_BE_INITIALIZED_REPO, path, initialize_if_empty = True, gitignore_contents = path)
            self.assertEqual(initialized_repo._url, self.TO_BE_INITIALIZED_REPO)
            self.assertEqual(initialized_repo._default_branch, plcf_git.GIT.MASTER)
            self.assertEqual(initialized_repo._branch, plcf_git.GIT.MASTER)
            self.assertEqual(initialized_repo.get_current_branch(), plcf_git.GIT.MASTER)
            self.assertTrue(os.path.isfile(os.path.join(path, ".gitignore")))
#            with open(os.path.join(path, ".gitignore"), "r") as gitignore:
#                self.assertListEqual(gitignore.readlines(), [path + "\n"])


    def test_multiple_branches_repo(self):
        with mkdtemp(prefix = "test-plcf-git-multiple-branches-repo") as path:
            mainfile = os.path.join(path, "main")
            masterfile = os.path.join(path, "master")

            multiple_branches_repo = plcf_git.GIT.clone(self.MULTIPLE_BRANCHES_REPO, path)
            self.assertEqual(multiple_branches_repo._url, self.MULTIPLE_BRANCHES_REPO_GIT)
            self.assertEqual(multiple_branches_repo._default_branch, "main")

            def test_main():
                self.assertEqual(multiple_branches_repo._branch, "main")
                self.assertEqual(multiple_branches_repo.get_current_branch(), "main")

                self.assertTrue(os.path.isfile(mainfile))
                self.assertFalse(os.path.isfile(masterfile))
                with open(mainfile, "r") as main:
                    self.assertListEqual(main.readlines(), ["main\n"])

            test_main()

            multiple_branches_repo.checkout("master")
            self.assertEqual(multiple_branches_repo._branch, "master")
            self.assertEqual(multiple_branches_repo.get_current_branch(), "master")

            self.assertFalse(os.path.isfile(mainfile))
            self.assertTrue(os.path.isfile(masterfile))
            with open(masterfile, "r") as master:
                self.assertListEqual(master.readlines(), ["master\n"])

            # 'Clone' with explicit branch using existing working copy
            multiple_branches_repo = plcf_git.GIT.clone(self.MULTIPLE_BRANCHES_REPO, path, branch = "main")
            self.assertEqual(multiple_branches_repo._url, self.MULTIPLE_BRANCHES_REPO_GIT)
            self.assertEqual(multiple_branches_repo._default_branch, "main")

            test_main()



def main():
    unittest.main()


if __name__ == "__main__":
    main()
