from __future__ import print_function

from shlex import split as shlex_split
import subprocess



def get_local_ref():
    try:
        return subprocess.check_output(shlex_split("git rev-parse master")).strip()
    except subprocess.CalledProcessError:
        return None


def get_remote_ref():
    try:
        output = subprocess.check_output(shlex_split("git ls-remote --quiet --exit-code origin refs/heads/master"))
        return output[:-len("refs/heads/master\n")].strip()
    except subprocess.CalledProcessError:
        return None




if __name__ == "__main__":
    print("Local ref:", get_local_ref())
    print("Remote ref:", get_remote_ref())
