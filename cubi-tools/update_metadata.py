#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import toml


def main():
    files_updated = False
    args = parse_command_line()
    project_dir = args.project_dir.resolve()
    print(f"Project directory set as: {project_dir}")
    ref_repo_clone = args.ref_repo_clone
    ref_repo_curl = args.ref_repo_curl
    ref_repo_wget = args.ref_repo_wget
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
        if f == "pyproject.toml":
            print(f"files_updated? {files_updated}")
            if files_updated:
                update_pyproject_toml(metadata_dir, ref_repo_wget)
        else:
            files_updated = (
                update_file(f, metadata_dir, ref_repo_curl, ref_repo_wget)
                or files_updated
            )


def parse_command_line():
    parser = argp.ArgumentParser(
        description="Add or update metadata files for your repository. Example: python3 add-update-metadata.py --project-dir path/to/repo"
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
        default="https://raw.githubusercontent.com/core-unit-bioinformatics/template-metadata-files/main/",
        help="Reference/remote repository used to wget files.",
    )
    parser.add_argument(
        "--external",
        "-s",
        action="store_true",
        default=False,
        dest="external",
        help="If False (default), metafiles are copied to the project location, else to a subfolder (cubi).",
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
    print(f"External set as: {external}")
    if external:
        print("Assuming external repository (workflow)")
        return True
    else:
        print(
            "Assuming non-external repository (workflow), you can change this with --external"
        )
        return False


def metadatafiles_present(project_dir, external):
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


def clone(project_dir, ref_repo_clone, external):  # copy all metafiles
    if not external:
        sp.call(
            [
                "git",
                "clone",
                "--depth=1",
                "--branch=main",  # depth =1 to avoid big .git file
                ref_repo_clone,
                project_dir,
            ],
            cwd=project_dir,
        )
    else:
        pathlib.Path(project_dir, "cubi").mkdir(parents=True, exist_ok=True)
        cubi_path = pathlib.Path(project_dir, "cubi")
        sp.call(
            [
                "git",
                "clone",
                "--depth=1",
                "--branch=main",  # depth =1 to avoid big .git file
                ref_repo_clone,
                cubi_path,
            ],
            cwd=cubi_path,
        )


def get_local_checksum(metadata_dir, f):
    command = ["git", "hash-object", metadata_dir.joinpath(f)]
    sha1Sum = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=metadata_dir,
    )
    return sha1Sum.stdout.strip()


def get_ref_checksum(ref_repo_curl, f, project_dir):
    command = [
        "curl",
        ref_repo_curl + f,
    ]
    sha1SumRef = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=project_dir,
    )
    return sha1SumRef.stdout.split('"')[11]


def update_pyproject_toml(metadata_dir, ref_repo_wget):
    f = "pyproject.toml"
    user_response = input(f"Update metadata files version in {f}? (y/n)")
    answers = {
        "yes": True,
        "y": True,
        "yay": True,
        "no": False,
        "n": False,
        "nay": False,
    }
    try:
        do_update = answers[user_response]
    except KeyError:
        raise ValueError(
            f"That was a yes or no question, but you answered: {user_response}"
        )

    if do_update:
        if not pathlib.Path(metadata_dir, f).is_file():
            command = ["wget", ref_repo_wget + f, "-O" + f]
            sp.call(command, cwd=metadata_dir)
        command = [
            "wget",
            ref_repo_wget + f,
            "-O" + f + ".temp",
        ]  # -O to overwrite existing file
        sp.call(command, cwd=metadata_dir)
        version_new = toml.load(pathlib.Path(metadata_dir, f + ".temp"), _dict=dict)
        version_new = toml.load(pathlib.Path(metadata_dir, f + ".temp"), _dict=dict)
        version_old = toml.load(pathlib.Path(metadata_dir, f), _dict=dict)
        version_new = version_new["cubi"]["metadata"]["version"]
        version_old_print = version_old["cubi"]["metadata"]["version"]
        version_old["cubi"]["metadata"]["version"] = version_new
        toml.dumps(version_old, encoder=None)
        with open(pathlib.Path(metadata_dir, f), "w") as text_file:
            text_file.write(toml.dumps(version_old, encoder=None))
        pathlib.Path(metadata_dir, f + ".temp").unlink()
        print(f"{f} updated from version {version_old_print} to version {version_new}!")


def update_file(f, metadata_dir, ref_repo_curl, ref_repo_wget):
    local_sum = get_local_checksum(metadata_dir, f)
    ref_sum = get_ref_checksum(ref_repo_curl, f, metadata_dir)
    if local_sum != ref_sum:
        print(f"File: {f} differs.")
        print(f"Local SHA checksum: {local_sum}")
        print(f"Remote SHA checksum: {ref_sum}")
        user_response = input(f"Update {f}? (y/n)")
        answers = {
            "yes": True,
            "y": True,
            "yay": True,
            "no": False,
            "n": False,
            "nay": False,
        }
        try:
            do_update = answers[user_response]
        except KeyError:
            raise ValueError(
                f"That was a yes or no question, but you answered: {user_response}"
            )

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
            print(f"{f} nothing to update.")
    else:
        return False
        print("f{f} nothing to update.")


def report_script_version():
    toml_file = pathlib.Path(pathlib.Path(__file__).resolve().parent, "pyproject.toml")
    toml_file = toml.load(toml_file, _dict=dict)
    version = toml_file["cubi"]["devtools"]["script"][0]["version"]
    return version


if __name__ == "__main__":
    main()
