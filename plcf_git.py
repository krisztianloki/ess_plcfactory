from __future__ import print_function

import os
from shlex import split as shlex_split
import subprocess
import time

__git_dir = (os.path.abspath(os.path.dirname(__file__)))


def get_status(cwd = None):
    # Returns True if clean
    if cwd is None:
        cwd = __git_dir
    try:
        return subprocess.check_output(shlex_split("git status -uno --porcelain"), cwd = __git_dir).strip() == ""
    except subprocess.CalledProcessError:
        return False


def clone(url, cwd, branch = None):
    try:
        return subprocess.check_call(shlex_split("git clone --quiet {} {} .".format(url, "" if branch is None else "--branch {} --depth 1".format(branch))), cwd = cwd)
    except subprocess.CalledProcessError as e:
        print(e)
        raise


def checkout(cwd, version):
    try:
        return subprocess.check_call(shlex_split("git checkout --quiet {}".format(version)), cwd = cwd)
    except subprocess.CalledProcessError as e:
        print(e)
        raise


def get_current_branch():
    try:
        return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD"), cwd = __git_dir).strip()
    except subprocess.CalledProcessError:
        return None


def get_local_ref(branch = "master"):
    try:
        return subprocess.check_output(shlex_split("git rev-parse {}".format(branch)), cwd = __git_dir).strip()
    except subprocess.CalledProcessError:
        return None


def get_remote_ref(branch = "master"):
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --quiet --exit-code origin refs/heads/{}".format(branch)), cwd = __git_dir)
        return output[:-len("refs/heads/{}\n".format(branch))].strip()
    except subprocess.CalledProcessError:
        return None


def has_commit(commit):
    try:
        # Cannot use check_call; have to redirect stderr...
        subprocess.check_output(shlex_split("git cat-file -e {}^{{commit}}".format(commit)), stderr = subprocess.STDOUT, cwd = __git_dir)
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
    remote_ref = get_remote_ref()
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
