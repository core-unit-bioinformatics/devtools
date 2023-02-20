#!/usr/bin/env python3

import argparse as argp
import collections as col
import pathlib as pl
import subprocess as sp
import sys

import toml


Remote = col.namedtuple("Remote", "name org priority")


def _extract_version():
    """TODO
    This function should be
    moved into a common
    package code base for all
    devtools
    """

    script_location = pl.Path(__file__).resolve(strict=True)
    repo_path = script_location.parent.parent
    assert repo_path.name == "devtools"
    pyproject_file = repo_path.joinpath("pyproject.toml").resolve(strict=True)
    pyproject_desc = toml.load(pyproject_file)

    script_version = None
    for script_metadata in pyproject_desc["cubi"]["devtools"]["script"]:
        if __prog__ == script_metadata["name"]:
            script_version = script_metadata["version"]
            break
    if script_version is None:
        err_msg = (
            f"No version number defined for this script ({__prog__})\n"
            f"in pyproject.toml located at {pyproject_file}!"
        )
        raise ValueError(err_msg)
    return script_version


__prog__ = "auto_git.py"
__version__ = _extract_version()
__author__ = "Peter Ebert"
__license__ = "MIT"
__full_version__ = f"{__prog__} v{__version__} ({__license__} license)"


KNOWN_REMOTES = {
    "github.com": Remote("github", "core-unit-bioinformatics", 1),
    "git.hhu.de": Remote("githhu", "cubi", 0)
}


def parse_command_line():

    parser = argp.ArgumentParser(prog=__prog__)
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=__full_version__,
        help="Show version and exit."
    )
    mutex = parser.add_mutually_exclusive_group(required=True)
    mutex.add_argument(
        "--clone",
        "-c",
        type=str,
        default=None,
        dest="clone",
        help="Full (remote) git path to clone in the form of: git@<remote>:<user>/<repo>.git"
    )
    mutex.add_argument(
        "--init",
        "-i",
        type=str,
        default=None,
        dest="init",
        help="Name of the new repository to initialize"
    )
    mutex.add_argument(
        "--norm",
        "-n",
        type=lambda x: pl.Path(x).resolve(strict=True),
        default=None,
        dest="norm",
        help="Normalize git remotes."
    )
    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-dry",
        "-d",
        action="store_true",
        dest="dryrun",
        default=False,
        help="Just print what you would do, but don't do it"
    )
    default_git_id_folder = pl.Path.home().joinpath(".identities")
    parser.add_argument(
        "--git-identities",
        "-g",
        type=lambda x: pl.Path(x).resolve(strict=False),
        dest="identities",
        default=default_git_id_folder,
        help="Path to folder with github identities for remotes. "
             f"Default: {default_git_id_folder}/*.id"
    )
    parser.add_argument(
        "--no-all-target",
        "--no-all",
        "-noa",
        action="store_true",
        default=False,
        dest="no_all",
        help="Do not configure multiple push targets / do not add 'all' remote. Default: False"
    )
    parser.add_argument(
        "--no-user-config",
        "--no-cfg",
        "-noc",
        action="store_true",
        default=False,
        dest="no_config",
        help="Do not configure user name and email for git repository. Default: False"
    )
    args = parser.parse_args()

    if not args.no_config:
        if not args.identities.is_dir():
            raise ValueError(
                "Configuring user name / email requires valid "
                "path to identities folder with one identity "
                "file per git remote (pattern: <remote>.id). "
                "Identity folder path is currently set to\n"
                f"{default_git_id_folder}"
            )

    return args


def parse_git_url(url):

    prefix, remainder = url.split("@")
    remainder, suffix = remainder.rsplit(".", 1)
    assert prefix == suffix == "git"
    remote_by_url, remainder = remainder.split(":", 1)
    assert remote_by_url in KNOWN_REMOTES
    user_or_org, remainder = remainder.split("/", 1)
    repo_name = remainder
    infos = {
        "remote_url": remote_by_url,
        "remote_name": KNOWN_REMOTES[remote_by_url].name,
        "user": user_or_org,
        "repo_name": repo_name,
        "priority": KNOWN_REMOTES[remote_by_url].priority
    }
    return infos


def set_push_targets(git_infos, wd, is_init, dry_run):

    all_remote_paths = []
    for remote_url, remote in KNOWN_REMOTES.items():
        remote_git_path = f"git@{remote_url}:{remote.org}/{git_infos['repo_name']}.git"
        all_remote_paths.append(remote_git_path)
        cmd = " ".join(
            [
                "git", "remote", "add",
                f"{remote.name}", remote_git_path
            ])
        if remote_url == git_infos["remote_url"] and is_init:
            # since this repo was locally created,
            # the primary remote still needs to be set
            execute_command(cmd, wd, dry_run)
        elif remote_url == git_infos["remote_url"]:
            continue
        execute_command(cmd, wd, dry_run)

    primary_remote = f"git@{git_infos['remote_url']}:"
    primary_remote += f"{git_infos['user']}/"
    primary_remote += f"{git_infos['repo_name']}.git"
    # set all remote
    cmd = " ".join(
        [
            "git", "remote", "add",
            "all", primary_remote
        ])
    execute_command(cmd, wd, dry_run)
    for remote_path in all_remote_paths:
        cmd = " ".join(
            [
                "git", "remote", "set-url",
                "--add", "--push", "all",
                remote_path
            ])
        execute_command(cmd, wd, dry_run)
    return


def get_git_id_settings(id_folder, remote_name):

    id_file = id_folder.joinpath(f"{remote_name}.id").resolve(strict=True)
    with open(id_file, "r") as id_content:
        id_name = id_content.readline().strip().strip('"')
        id_email = id_content.readline().strip().strip('"')
    settings = [
        ("user.name", '"' + id_name + '"'),
        ("user.email", '"' + id_email + '"')
    ]
    return settings


def set_git_identity(git_infos, wd, id_folder, dry_run):

    primary_remote = git_infos["remote_name"]
    settings = get_git_id_settings(id_folder, primary_remote)
    for key, value in settings:
        cmd = " ".join(
            [
                "git", "config",
                key, value
            ])
        execute_command(cmd, wd, dry_run)
    return


def execute_command(cmd, wd, dry_run):

    if dry_run:
        msg = (
            "\nWould execute...\n"
            f"\tin directory: {wd}\n"
            f"\tthis command: {cmd}\n"
        )
        sys.stdout.write(msg)
        # prevent unbound local
        # for dry run
        out = b""
    else:
        try:
            out = sp.check_output(cmd, shell=True, cwd=wd)
        except sp.CalledProcessError as perr:
            sys.stderr.write(f"\nError for command: {perr.cmd}\n")
            sys.stderr.write(f"Exit status: {perr.returncode}\n")
            sys.stderr.write(f"Message: {perr.output.decode('utf-8')}\n")
            raise
    return out.decode("utf-8").strip()


def clone_git(args, wd):
    """ Clone a repository, add
    all push target (default: yes);
    configure user name and email
    (default: yes)
    """
    git_infos = parse_git_url(args.clone)
    cmd = " ".join(
        [
            "git", "clone",
            f"--origin {git_infos['remote_name']}",
            args.clone
        ]
    )
    _ = execute_command(cmd, wd, args.dryrun)
    repo_wd = wd.joinpath(git_infos["repo_name"])
    if not args.no_all:
        set_push_targets(git_infos, repo_wd, False, args.dryrun)
    if not args.no_config:
        set_git_identity(git_infos, repo_wd, args.identities, args.dryrun)

    return


def norm_git(args, wd):
    """ Normalize remote name,
    add all push target (default: yes);
    configure user name and email
    (default: yes)
    """
    cmd = " ".join(
        [
            "git", "remote", "-v"
        ]
    )
    # the following only reads info,
    # no need to exec as dry run
    remotes = execute_command(cmd, wd, False)
    set_remotes = []
    for remote in remotes.split("\n"):
        if "push" in remote:
            continue
        current_name, remote_url, _ = remote.strip().split()
        if current_name == "all":
            # seems unlikely, but if configured,
            # leave as is
            print(f"Skipping over 'all': {remote_url}")
            continue
        remote_infos = parse_git_url(remote_url)
        if remote_infos["remote_name"] != current_name:
            cmd = " ".join(
                [
                    "git", "remote", "rename",
                    current_name, remote_infos["remote_name"]
                ]
            )
            _ = execute_command(cmd, wd, args.dryrun)
        set_remotes.append(
            (remote_infos["priority"], remote_infos)
        )
    set_remotes = sorted(set_remotes, reverse=True)
    primary_remote = set_remotes[0][1]
    if not args.no_all:
        set_push_targets(
            primary_remote, wd,
            False, args.dryrun
        )
    if not args.no_config:
        set_git_identity(
            primary_remote, wd,
            args.identities, args.dryrun
        )
    return
    


def init_git(args, wd):
    raise NotImplementedError


def main():

    args = parse_command_line()
    wd = pl.Path(".").resolve()
    if args.clone is not None:
        clone_git(args, wd)
    elif args.init is not None:
        init_git(args, wd)
    elif args.norm is not None:
        wd = args.norm.resolve(strict=True)
        assert wd.joinpath(".git").is_dir()
        norm_git(args, wd)
    else:
        raise ValueError("No action specified")

    return 0


if __name__ == "__main__":
    main()
