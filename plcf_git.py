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
    REMOTE_PREFIX = "remote:"
    REMOTE_PREFIX_LEN = len(REMOTE_PREFIX)

    def __init__(self, path):
        super(GIT, self).__init__()

        self._path = path
        self._branch = None
        self._url = None


    def path(self):
        return self._path


    def url(self):
        return self._url


    @staticmethod
    def __is_repo(path):
        """
        Returns True if 'path' is inside a work tree of a git repository
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --is-inside-work-tree"), stderr = subprocess.STDOUT, cwd = path, **spkwargs).strip().lower() == "true"
        except subprocess.CalledProcessError as e:
            if e.output.strip() == "fatal: Not a git repository (or any of the parent directories): .git":
                return False

            raise


    @staticmethod
    def clone(url, path = '.', branch = None, update = False):
        """
        Clone the repository at 'url' into 'path' and possibly checkout 'branch'

        If repository is already cloned, checkout 'branch'

        If 'update' is True then the master branch will be updated
        """
        git = GIT(path)
        if not git.is_repo():
            # If 'path' is not a repository then clone url
            git.__clone(url, branch)
            return git

        if git.get_toplevel_dir() != path:
            # This is some other repository working tree, we can clone a new one here
            git.__clone(url, branch)
            return git

        # Have to check if this repository is the one we need
        if helpers.url_strip_user(git.get_origin()) != helpers.url_strip_user(url):
            raise GITException("Found unrelated git repository in {}, refusing to overwrite".format(path))

        git.__set_url(url)

        # Check if there are branches (meaning the repository is not empty) and do a git pull
        if update and git.get_branches():
            if git.get_current_branch() == "master":
                git.pull("master")
            else:
                # Not on master, so fetch master and also fetch remote tags
                git.fetch("master", "master")
                git.fetch_tags()

        # Check if we need to (and actually can) checkout 'branch'
        if branch and git.get_branches():
            git.checkout(branch)
        else:
            # Update the current branch
            git._branch = git.get_current_branch()

        return git


    def get_toplevel_dir(self):
        """
        Returns the toplevel directory of the repository
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --show-toplevel"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def get_origin(self):
        """
        Returns the remote url of 'origin'
        """
        try:
            return subprocess.check_output(shlex_split("git ls-remote --get-url origin"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def __set_url(self, url):
        if not url.endswith(".git"):
            url += ".git"
        self._url = url


    def __clone(self, url, branch = None):
        """
        Clone 'url'. If branch is specified then that branch is checked out
        """
        try:
            subprocess.check_output(shlex_split("git clone --quiet {} {} .".format(url, "" if branch is None else "--branch {} --depth 1".format(branch))), cwd = self._path, stderr = subprocess.STDOUT, **spkwargs)
            self.__set_url(url)
            self._branch = "master"
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def is_repo(self):
        return self.__is_repo(self._path)


    def checkout(self, branch, exception = False):
        """
        Checks out 'branch'
        """
        try:
            subprocess.check_call(shlex_split("git checkout --quiet {}".format(branch)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            self._branch = branch
            if exception:
                raise


    def create_branch(self, branch, start_point = None):
        """
        Creates and checks out 'branch' with starting point of 'start_point' (if specified)
        """
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
        """
        Returns the hashes(?) of the available branches
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --branches"), cwd = self._path, **spkwargs).splitlines()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def get_current_branch(self):
        """
        Returns the current branch
        """
        try:
            return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = self._path, **spkwargs).strip()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def add(self, files):
        """
        Adds the files in 'files'
        """
        try:
            if isinstance(files, str):
                files = [ files ]
            return subprocess.check_call(shlex_split("git add {}".format(" ".join(map(lambda x: os.path.relpath(x, self._path), files)))), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def remove(self, files):
        """
        Removes the files in 'files'
        """
        try:
            if isinstance(files, str):
                files = [ files ]
            return subprocess.check_call(shlex_split("git rm --quiet {}".format(" ".join(map(lambda x: os.path.relpath(x, self._path), files)))), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def commit(self, msg = None):
        """
        Commits the current contents of the index
        """
        try:
            if msg:
                msg = "-m '{}'".format(msg)
            else:
                msg = ""
            return subprocess.check_call(shlex_split("git commit --quiet {}".format(msg)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def remote_tags(self):
        """
        Returns the remote tags

        A list of lines as returned by 'git ls-remote --tags'
        """
        try:
            return subprocess.check_output(shlex_split("git ls-remote --tags origin"), cwd = self._path, **spkwargs).splitlines()
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def __filter_tag_names(self, ls_remote_output):
        """
        Removes the commit hashes and the refs/tags/ part of the tags. Also removes tags with the ^{} suffix
        """
        return filter(lambda x: not x.endswith("^{}"), map(lambda x: x[x.index("refs/tags/") + 10:], ls_remote_output))


    def tag(self, tag, msg = None, override_local = False):
        """
        Tags using 'msg' as commit message or 'tag' if 'msg' is not specified

        If 'override_local' is True it will overwrite existing _local_ tags
        """
        try:
            if msg is None:
                msg = tag
            msg = "-m '{}'".format(msg)

            if tag in self.__filter_tag_names(self.remote_tags()):
                raise GITException("Tag '{}' already exists".format(tag))
            else:
                if override_local:
                    force = "-f "
                else:
                    force = ""

            return subprocess.check_output(shlex_split("git tag -a {} {} {}".format(tag, force, msg)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            if e.output.strip() == "fatal: tag '{}' already exists".format(tag):
                raise GITException("Tag '{}' already exists".format(tag))
            print(e)
            raise


    def push(self):
        """
        Pushes the current branch

        Returns a URL to create a merge request
        """
        try:
            subprocess.check_call(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), cwd = self._path, **spkwargs)
            if helpers.url_to_host(self._url) == "gitlab.esss.lu.se":
                return "{url}/-/merge_requests/new?merge_request%5Bsource_branch%5D={branch}".format(url = self._url[:-4], branch = self._branch)
            # For some reason subprocess will hang when trying to capture the 'remote:' messages
            # subprocess.run() is not available in Python2

#            lines = subprocess.check_output(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), stderr = subprocess.STDOUT, cwd = self._path, **spkwargs).splitlines()

#            out = subprocess.run(shlex_split("git push --follow-tags --quiet --porcelain origin {}".format(self._branch)), stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = self._path, **spkwargs)
#            print(out)
#            lines = out.stderr.splitlines()

#            out = subprocess.Popen(shlex_split("git push --follow-tags --porcelain origin {}".format(self._branch)), stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = self._path, **spkwargs)
#            print("out:", out)
#            print("Calling communicate()")
#            output, stderr = out.communicate()
#            print("Calling poll()...")
#            retcode = out.poll()
#            if retcode:
#                raise subprocess.CalledProcessError(retcode, "git push", output = stderr)
#            print("STDOUT", output)
#            print("STDERR", stderr)
#            lines = stderr.splitlines()

#            print(lines)
#            lines = map(lambda l: l.strip()[GIT.REMOTE_PREFIX_LEN:].strip() if l.strip().startswith(GIT.REMOTE_PREFIX) else l.strip(), lines)
#            print(lines)
#            found = False
#            for l in lines:
#                if not l:
#                    continue
#
#                if l == "To create a merge request for {}, visit:".format(self._branch):
#                    print("Found",l)
#                    found = True
#                    continue
#
#                if found:
#                    # Return the link to merge request creation
#                    print("Link:", l)
#                    return l
            return None
        except subprocess.CalledProcessError as e:
            if e.output.startswith("fatal: Authentication failed for "):
                raise GITException("AUTHENTICATION PROBLEM")
            print(e)
            raise


    def fetch(self, src, dst = None):
        """
        Fetches 'src' into 'dst'
        """
        try:
            if dst:
                dst = ":" + dst
            subprocess.check_call(shlex_split("git fetch --quiet origin {}{}".format(src, dst)), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def fetch_tags(self):
        """
        Fetches tags
        """
        try:
            subprocess.check_call(shlex_split("git fetch --quiet --tags origin"), cwd = self._path, **spkwargs)
        except subprocess.CalledProcessError as e:
            print(e)
            raise


    def pull(self, src):
        """
        Pulls 'src'
        """
        try:
            subprocess.check_call(shlex_split("git pull --ff-only --quiet origin {}".format(src)), cwd = self._path, **spkwargs)
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
