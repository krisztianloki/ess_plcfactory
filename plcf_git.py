from __future__ import print_function

import helpers

import os
from shlex import split as shlex_split
import subprocess
import time

__git_dir = (os.path.abspath(os.path.dirname(__file__)))
try:
    isinstance('h', unicode)
    spkwargs = dict()
except:
    spkwargs = {'encoding':'utf8'}


class GITException(Exception):
    pass



class GIT(object):
    def __init__(self, path):
        super(GIT, self).__init__()

        self._path = path
        self._branch = None
        self._repo = None


    @staticmethod
    def __is_repo(path):
        try:
            return subprocess.check_output(shlex_split("git rev-parse --is-inside-work-tree"), stderr = subprocess.STDOUT, cwd = path, **spkwargs).strip().lower() == "true"
        except subprocess.CalledProcessError as e:
            if e.output.strip() == "fatal: Not a git repository (or any of the parent directories): .git":
                return False

            raise


    @staticmethod
    def clone(url, path = '.', branch = None):
        """
        Clone the repository at 'url' into 'path' and possibly checkout 'branch'

        If repository is already cloned, checkout 'branch'
        """
        git = GIT(path)
        if not git.is_repo():
            # If 'path' is not a repository then clone url
            print("Not repository --> clone")
            git.__clone(url, branch)
            return git

        if git.get_toplevel_dir() != path:
            # This is some other repository working tree, we can clone a new one here
            print("Inside other repository --> clone")
            git.__clone(url, branch)
            return git

        # Have to check if this repository is the one we need
        if helpers.url_strip_user(git.get_origin()) != helpers.url_strip_user(url):
            raise GITException("Found unrelated git repository in {}, refusing to overwrite".format(path))

        # Check if we need to (and actually can) checkout 'branch'
        if branch and git.get_branches():
            print("Checking out", branch)
            git.checkout(branch)
        else:
            # Update the current branch
            self._branch = self.get_current_branch()

        return git


    def get_toplevel_dir(self):
        try:
            return subprocess.check_output(shlex_split("git rev-parse --show-toplevel"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def get_origin(self):
        try:
            return subprocess.check_output(shlex_split("git ls-remote --get-url origin"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def __clone(self, url, branch = None):
        """
        Clone 'url'. If branch is specified then that branch is checked out
        """
        try:
            subprocess.check_output(shlex_split("git clone --quiet {} {} .".format(url, "" if branch is None else "--branch {} --depth 1".format(branch))), cwd = self._path, stderr = subprocess.STDOUT, **spkwargs)
            self._repo = url
            self._branch = "master"
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def is_repo(self):
        return self.__is_repo(self._path)


    def checkout(self, branch, exception = False):
        try:
            subprocess.check_call(shlex_split("git checkout --quiet {}".format(branch)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            self._branch = branch
            if exception:
                raise


    def create_branch(self, branch, start_point = None):
        try:
            if start_point:
                start_point = " {}".format(start_point)
            subprocess.check_output(shlex_split("git checkout --quiet -b {}{}".format(branch, start_point)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
            self._branch = branch
        except subprocess.CalledProcessError as e:
            if e.output.startswith("fatal: Cannot update paths and switch to branch '{}' at the same time.".format(branch)):
                raise GITException("Branch {} does not exist".format(start_point))
            print(e)
            raise


    def get_branches(self):
        try:
            return subprocess.check_output(shlex_split("git rev-parse --branches"), cwd = self._path, **spkwargs).splitlines()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def get_current_branch(self):
        try:
            return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def add(self, files):
        try:
            if isinstance(files, str):
                files = [ files ]
            return subprocess.check_call(shlex_split("git add {}".format(" ".join(files))), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def commit(self, msg = None):
        try:
            if msg:
                msg = "-m '{}'".format(msg)
            else:
                msg = ""
            return subprocess.check_call(shlex_split("git commit --quiet {}".format(msg)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def tag(self, tag, msg = None):
        try:
            if msg is None:
                msg = tag
            msg = "-m '{}'".format(msg)

            return subprocess.check_call(shlex_split("git tag -a {} {}".format(tag, msg)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def push(self):
        try:
            subprocess.check_call(shlex_split("git push --follow-tags origin {}".format(self._branch)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise



def get_status(cwd = None):
    # Returns True if clean
    if cwd is None:
        cwd = __git_dir
    try:
        return subprocess.check_output(shlex_split("git status -uno --porcelain"), cwd = __git_dir, **spkwargs).strip() == ""
    except subprocess.CalledProcessError:
        return False


def clone(url, cwd, branch = None):
    try:
        return subprocess.check_call(shlex_split("git clone --quiet {} {} .".format(url, "" if branch is None else "--branch {} --depth 1".format(branch))), cwd = cwd, **spkwargs)
    except subprocess.CalledProcessError as e:
        print(e)
        raise


def checkout(cwd, version):
    try:
        return subprocess.check_call(shlex_split("git checkout --quiet {}".format(version)), cwd = cwd, **spkwargs)
    except subprocess.CalledProcessError as e:
        print(e)
        raise


def get_origin():
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --get-url origin"), cwd = __git_dir, **spkwargs)
        return output.strip()
    except subprocess.CalledProcessError:
        return None


def get_current_branch():
    try:
        return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = __git_dir, **spkwargs).strip()
    except subprocess.CalledProcessError:
        return None


def get_local_ref(branch = "master"):
    try:
        return subprocess.check_output(shlex_split("git rev-parse {}".format(branch)), cwd = __git_dir, **spkwargs).strip()
    except subprocess.CalledProcessError:
        return None


def get_remote_ref(branch = "master"):
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --quiet --exit-code origin refs/heads/{}".format(branch)), cwd = __git_dir, **spkwargs)
        return output[:-len("refs/heads/{}\n".format(branch))].strip()
    except subprocess.CalledProcessError:
        return None


def has_commit(commit):
    try:
        # Cannot use check_call; have to redirect stderr...
        subprocess.check_output(shlex_split("git cat-file -e {}^{{commit}}".format(commit)), stderr = subprocess.STDOUT, cwd = __git_dir, **spkwargs)
        return True
    except subprocess.CalledProcessError:
        return False


def check_for_updates(data_dir, product):
    local_ref = get_local_ref()

    if local_ref is None:
        print("Could not check local version")
        return False

    check_time = time.time()

    try:
        with open(os.path.join(data_dir, "updates")) as u:
            raw_updates = u.readline()
        from ast import literal_eval as ast_literal_eval
        updates = ast_literal_eval(raw_updates)
        if updates[0] + 600 > check_time:
            if local_ref != updates[1]:
                print("An update is available")
            return False
    except:
        pass

    print("Checking for updates...")
    try:
        remote_ref = get_remote_ref()
    except KeyboardInterrupt:
        remote_ref = None
    if remote_ref is None:
        print("Could not check for updates")
        return False

    # Check if we have remote ref. True means we are most probably ahead of origin; ignore remote ref then
    if has_commit(remote_ref):
        remote_ref = local_ref

    updates = (check_time, remote_ref)
    try:
        with open(os.path.join(data_dir, "updates"), "w") as u:
            print(updates, file = u)
    except:
        pass

    if remote_ref != local_ref:
        print("""
An update to {} is available.

Please run `git pull`
""".format(product))
        return True

    return False





if __name__ == "__main__":
    print("Local ref:", get_local_ref())
    print("Remote ref:", get_remote_ref())
