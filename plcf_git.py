from __future__ import print_function

from shlex import split as shlex_split
import subprocess



def get_current_branch():
    try:
        return subprocess.check_output(shlex_split("git rev-parse --abbrev-ref HEAD")).strip()
    except subprocess.CalledProcessError:
        return None


def get_local_ref(branch = "master"):
    try:
        return subprocess.check_output(shlex_split("git rev-parse {}".format(branch))).strip()
    except subprocess.CalledProcessError:
        return None


def get_remote_ref(branch = "master"):
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --quiet --exit-code origin refs/heads/{}".format(branch)))
        return output[:-len("refs/heads/{}\n".format(branch))].strip()
    except subprocess.CalledProcessError:
        return None


def has_commit(commit):
    try:
        subprocess.check_call(shlex_split("git cat-file -e {}^{{commit}}".format(commit)))
        return True
    except subprocess.CalledProcessError:
        return False




if __name__ == "__main__":
    print("Local ref:", get_local_ref())
    print("Remote ref:", get_remote_ref())
