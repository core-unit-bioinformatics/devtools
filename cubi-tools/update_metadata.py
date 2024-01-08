#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import toml


def main():
    """Description of what this function does."""
    files_updated = False
    args = parse_command_line()
    project_dir = args.project_dir.resolve()
    print(f"Project directory set as: {project_dir}")
    ref_repo_curl = args.ref_repo_curl
    branch = args.branch
    ref_repo_wget = args.ref_repo_wget + branch + "/"
    external = args.external

    # report version of script
    if args.version:
        print(f"Script version: {report_script_version()}")

    # detect if its a external workflow
    external = is_external(external)
    if external:
        metadata_dir = pathlib.Path(project_dir, "cubi")
        metadata_dir.mkdir(parents=True, exist_ok=True)
    else:
        metadata_dir = project_dir

    files_to_update = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
        "pyproject.toml",
    ]
    print(f"Metadata directory set as: {metadata_dir}")

    for f in files_to_update:
        print(f"{f} checking...")
        files_updated = update_file(f, metadata_dir, ref_repo_curl, branch, ref_repo_wget)
        update_file(f, metadata_dir, ref_repo_curl, branch, ref_repo_wget)
        if f == "pyproject.toml":
            print(f"files_updated? {files_updated}")
            if files_updated:
                update_pyproject_toml(metadata_dir, ref_repo_wget, ref_repo_curl, branch, f)
        else:
            files_updated = (
                update_file(f, metadata_dir, ref_repo_curl, branch, ref_repo_wget)
                or files_updated
            )
    return None


def parse_command_line():
    """Description of what this function does."""
    parser = argp.ArgumentParser(
        description="Add or update metadata files for your repository. "\
            "Example: python3 add-update-metadata.py --project-dir path/to/repo"
    )
    parser.add_argument(
        "--project-dir",
        type=pathlib.Path,
        help="(Mandatory) Directory where metadata should be copied/updated.",
        required=True,
    )
    parser.add_argument(
        "--ref-repo-clone",
        type=str,
        nargs="?",
        default="git@github.com:core-unit-bioinformatics/template-metadata-files.git",
        help="Reference/remote repository used to clone files.",
    )
    parser.add_argument(
        "--ref-repo-curl",
        type=str,
        nargs="?",
        default="https://api.github.com/repos/core-unit-bioinformatics/template-metadata-files/contents/",
        help="Reference/remote repository used to curl files.",
    )
    parser.add_argument(
        "--ref-repo-wget",
        type=str,
        nargs="?",
        default="https://raw.githubusercontent.com/core-unit-bioinformatics/template-metadata-files/",
        help="Reference/remote repository used to wget files.",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        default=False,
        dest="external",
        help="If False (default), metafiles are copied to the project location,"\
             "else to a subfolder (cubi).",
    )
    parser.add_argument(
        "--branch",
        type=str,
        nargs="?",
        default="main",
        help="Branch or Tag from which to update the files",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Displays version of this script.",
    )
    # if no arguments are given, print help
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()  # default is code 0
    args = parser.parse_args()
    return args


def is_external(external):
    """Description of what this function does."""
    print(f"External set as: {external}")
    if external:
        print("Assuming external repository (workflow)")
        return True
    else:
        print(
            "Assuming non-external repository (workflow),"\
            "you can change this with --external"
        )
        return False


def metadatafiles_present(project_dir, external):
    """Description of what this function does."""
    if external:
        if pathlib.Path(project_dir, "cubi").exists() and any(project_dir.iterdir()):
            return True
        else:
            return False
    else:
        if not any(project_dir.iterdir()):
            return False
        else:
            return True


def get_local_checksum(metadata_dir, f):
    """Description of what this function does."""
    command = ["git", "hash-object", metadata_dir.joinpath(f)]
    sha1sum = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=metadata_dir,
        check=False,
    )
    return sha1sum.stdout.strip()


def get_ref_checksum(ref_repo_curl, f, branch, project_dir):
    """Description of what this function does."""
    command = [
        "curl",
        ref_repo_curl + f + "?ref=" + branch,
    ]
    sha1sumref = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=project_dir,
        check=False,
    )
    sha1_output = sha1sumref.stdout
    api_issue = "API rate limit"
    if api_issue in sha1_output:
        raise Exception(
            "API rate limit exceeded. You have to wait until you can connect to the repository again!"
        )
    try:
        sha1_checksum = sha1sumref.stdout.split('"')[
            11
        ]  # The output of this command is the sha1 checksum for the file to update
    except IndexError as exc:
        raise IndexError(
            f"{branch} is not a valid branch/tag in this repository or"/
             "{f} doesn't exist in this branch/tag"
        ) from exc
    return sha1_checksum


def update_file(f, metadata_dir, ref_repo_curl, branch, ref_repo_wget):
    """Description of what this function does."""
    local_sum = get_local_checksum(metadata_dir, f)
    ref_sum = get_ref_checksum(ref_repo_curl, f, branch, metadata_dir)
    if local_sum != ref_sum:
        print(f"File: {f} differs.")
        print(f"Local SHA checksum: {local_sum}")
        print(f"Remote SHA checksum: {ref_sum}")
        user_response = input(f"Update {f}? (y/n)")
        answers = {
            "yes": True,
            "y": True,
            "Y": True,
            "yay": True,
            "no": False,
            "n": False,
            "N": False,
            "nay": False,
        }
        try:
            do_update = answers[user_response]
        except KeyError as exc:
            raise ValueError(
                f"That was a yes or no question, but you answered: {user_response}"
            ) from exc

        if do_update:
            command = [
                "wget",
                ref_repo_wget + f,
                "-O" + f,
            ]  # -O to overwrite existing file
            sp.call(command, cwd=metadata_dir)
            print(f"{f} updated!")
            return True
        else:
            return False
    else:
        return False

def update_pyproject_toml(metadata_dir, ref_repo_wget, ref_repo_curl, branch, f):
    """Description of what this function does."""
    updates = update_file(f, metadata_dir, ref_repo_curl, branch, ref_repo_wget)
    if updates == True:
        file = "pyproject.toml"
        user_response = input(f"Update metadata files version in {file}? (y/n)")
        answers = {
            "yes": True,
            "y": True,
            "Y": True,
            "yay": True,
            "no": False,
            "n": False,
            "N": False,
            "nay": False,
        }
        try:
            do_update = answers[user_response]
        except KeyError as exc:
            raise ValueError(
                f"That was a yes or no question, but you answered: {user_response}"
            ) from exc

        if do_update:
            if not pathlib.Path(metadata_dir, file).is_file():
                command = ["wget", ref_repo_wget + file, "-O" + file]
                sp.call(command, cwd=metadata_dir)
            command = [
                "wget",
                ref_repo_wget + file,
                "-O" + file + ".temp",
            ]  # -O to overwrite existing file
            sp.call(command, cwd=metadata_dir)
            version_new = toml.load(pathlib.Path(metadata_dir, file + ".temp"), _dict=dict)
            version_old = toml.load(pathlib.Path(metadata_dir, file), _dict=dict)
            version_new = version_new["cubi"]["metadata"]["version"]
            version_old_print = version_old["cubi"]["metadata"]["version"]
            version_old["cubi"]["metadata"]["version"] = version_new
            toml.dumps(version_old, encoder=None)
            with open(pathlib.Path(metadata_dir, file), "w", encoding="utf-8") as text_file:
                text_file.write(toml.dumps(version_old, encoder=None))
            pathlib.Path(metadata_dir, file + ".temp").unlink()
            print(f"{file} updated from version {version_old_print} to version {version_new}!")
            return True
        return True
    else:
        return False

def report_script_version():
    """Description of what this function does."""
    toml_file = pathlib.Path(
        pathlib.Path(__file__).resolve().parent.parent, "pyproject.toml"
    )
    toml_file = toml.load(toml_file, _dict=dict)
    version = toml_file["cubi"]["tools"]["script"][0]["version"]
    return version


if __name__ == "__main__":
    main()
