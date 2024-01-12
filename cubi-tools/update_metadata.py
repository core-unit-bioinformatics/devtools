#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import hashlib
import toml

# sys.tracebacklimit = -1


def main():
    """
    Main function of the 'update-metadata.py' script.
    """

    args = parse_command_line()
    dryrun = args.dryrun

    # Is it a dry run?
    if dryrun:
        print("\nTHIS IS A DRY RUN!!")

    # report version of script
    if args.version:
        print(f"\nScript version: {report_script_version()}")

    project_dir = args.project_dir.resolve()
    print(f"\nProject directory set as: {project_dir}")
    ref_repo = args.ref_repo
    source = args.source
    external = args.external
    keep = args.keep

    # location of the temp folder holding branch/version tag of interest
    temp_folder = pathlib.Path(f"{project_dir}/temp/{source}")

    # detect if its a external workflow
    if external:
        metadata_dir = external_repo(project_dir, external, dryrun)
        print(f"\nExternal set as: {external}\n")
        print(
            f"Metadata source directory set as: {external_repo(project_dir, external, dryrun)}\n"
        )
    else:
        metadata_dir = external_repo(project_dir, external, dryrun)
        print(
            f"Metadata source directory set as: {external_repo(project_dir, external, dryrun)}\n"
        )

    # Clone the 'template-metadata-files' branch or version tag into a local temp folder if it exists
    try:
        clone(project_dir, ref_repo, source, temp_folder, dryrun)
    except AssertionError:
        raise AssertionError(
            f"The repository you entered or the branch or version tag named '{source}' doesn't exist"
        ) from None

    # files that will be updated
    files_to_update = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
        "pyproject.toml",
    ]

    # Updating routine of the metadata files
    for f in files_to_update:
        print(f"{f} checking...")
        if f == "pyproject.toml":
            update_pyproject_toml(metadata_dir, temp_folder, dryrun)
        else:
            update_file(f, metadata_dir, temp_folder, dryrun)

    # detect if metafiles temp folder should be kept
    if keep:
        print(
            "\nYou want to keep the temp folder with the metadata file. "
            f"It's located at {temp_folder}"
        )
    else:
        rm_temp(temp_folder.parent, dryrun)
        print("\nThe temp folder with all metadata files and folders has been deleted!")

    return None


def parse_command_line():
    """
    Collection of the various options of the 'update-metadata.py' script.
    """
    parser = argp.ArgumentParser(
        description="Add or update metadata files for your repository. "
        "Example: python3 add-update-metadata.py --project-dir path/to/repo"
    )
    parser.add_argument(
        "--project-dir",
        type=pathlib.Path,
        help="(Mandatory) Directory where metadata should be copied/updated.",
        required=True,
    )
    parser.add_argument(
        "--ref-repo",
        type=str,
        nargs="?",
        default="https://github.com/core-unit-bioinformatics/template-metadata-files.git",
        help="Reference/remote repository used to clone files.",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        default=False,
        dest="external",
        help="If False (default), metafiles are copied to the project location,"
        "else to a subfolder (cubi).",
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        nargs="?",
        default="main",
        help="Branch or Tag from which to update the files",
    )
    parser.add_argument(
        "--keep",
        "-k",
        action="store_true",
        default=False,
        dest="keep",
        help="If False (default), the metafiles source repo will be deleted when script finishes,"
        "else it will be kept.",
    )
    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-d",
        "-dry",
        action="store_true",
        default=False,
        dest="dryrun",
        help="Just print what you would do, but don't do it",
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


def clone(metadata_dir, ref_repo, source, temp_folder, dryrun):
    """
    Check if the branch or version tag that contains the desired metadata files
    is already in a temp folder within the project directory.
    If that is not the case, the desired branch or version tag will be cloned into
    a temp folder within the project directory unless the branch or version tag don't exist,
    then an AssertionError will be called to stop the script.
    If a temp folder for the branch or version tag exists this folder is getting updated via
    a git pull command.
    """
    if dryrun:
        if not temp_folder.is_dir():
            print(
                f"The requested branch/version tag (default: main) is being copied to {temp_folder}."
            )
        else:
            print(
                "The requested branch/version tag (default: main) already exists and is getting updated."
            )
    else:
        if not temp_folder.is_dir():
            command = [
                "git",
                "clone",
                "-q",
                "-c advice.detachedHead=false",
                "--depth=1",  # depth =1 to avoid big .git file
                "--branch",
                source,
                ref_repo,
                temp_folder,
            ]
            clone_cmd = sp.run(
                command,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                cwd=metadata_dir,
                check=False,
            )
            # Git will throw a error message if you try to clone a repo/branch/tag
            # that doesn't exist that contains the string 'fatal:'
            warning = "fatal:"
            assert warning not in str(clone_cmd.stderr.strip())
        else:
            command = [
                "git",
                "pull",
                "--all",
                "-q",
                "--depth=1",  # depth =1 to avoid big .git file
            ]
            sp.run(
                command,
                cwd=temp_folder,
                check=False,
            )
    return None


def get_local_checksum(metadata_dir, f):
    """
    The MD5 checksum for all metadata files in the local project directory is determined.
    """
    if metadata_dir.joinpath(f).is_file():
        with open(metadata_dir.joinpath(f), "rb") as local_file:
            # read contents of the file
            local_data = local_file.read()
            # pipe contents of the file through
            md5_local = hashlib.md5(local_data).hexdigest()
    else:
        md5_local = ""
    return md5_local


def get_ref_checksum(temp_folder, f):
    """
    The MD5 checksum for all metadata files in the temp folder for the desired branch or version tag is determined.
    """
    with open(temp_folder.joinpath(f), "rb") as ref_file:
        # read contents of the file
        ref_data = ref_file.read()
        # pipe contents of the file through
        md5_ref = hashlib.md5(ref_data).hexdigest()
    return md5_ref


def update_file(f, metadata_dir, temp_folder, dryrun):
    """
    The MD5 checksum of the the local metadata file(s) and the metadata file(s) in the desired
    branch or version tag are being compared. If they differ a question to update for each different
    metadata file pops up. If an update is requested it will be performed.
    """
    if dryrun:
        print(f"Dry run! {f} updated!")
    else:
        local_sum = get_local_checksum(metadata_dir, f)
        ref_sum = get_ref_checksum(temp_folder, f)
        if local_sum != ref_sum:
            print(f"File: {f} differs.")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            question = user_response(f"Update {f}")

            if question:
                command = [
                    "cp",
                    temp_folder.joinpath(f),
                    metadata_dir.joinpath(f),
                ]
                sp.call(command, cwd=metadata_dir)
                print(f"{f} updated!")
            else:
                print(f"{f} NOT updated!")
        return None


def update_pyproject_toml(metadata_dir, temp_folder, dryrun):
    """
    The 'pyproject.toml' is treated a little bit differently. First, there is a check if
    the file even exists in the project directory. If that is not the case it will be copied
    into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.metadata.version (and only that information!)
    differs between the local and the requested branch or version tag version. If that is the case the
    cubi.metadata.version is getting updated.
    """
    x = "pyproject.toml"
    if dryrun:
        print(f"Dry run! {x} added or updated!")
    else:
        if not metadata_dir.joinpath(x).is_file():
            question = user_response(
                f"There is no pyproject.toml in your folder. Add {x}"
            )

            if question:
                command = [
                    "cp",
                    temp_folder.joinpath(x),
                    metadata_dir.joinpath(x),
                ]
                sp.call(command, cwd=metadata_dir)
                print(f"{x} added!")
            else:
                print(f"{x} NOT added!")

        else:
            command = [
                "cp",
                temp_folder.joinpath(x),
                pathlib.Path(metadata_dir, x + ".temp"),
            ]
            sp.call(command, cwd=metadata_dir)
            version_new = toml.load(pathlib.Path(metadata_dir, x + ".temp"), _dict=dict)
            version_old = toml.load(pathlib.Path(metadata_dir, x), _dict=dict)
            version_new = version_new["cubi"]["metadata"]["version"]
            version_old_print = version_old["cubi"]["metadata"]["version"]
            version_old["cubi"]["metadata"]["version"] = version_new

            if version_old_print != version_new:
                question = user_response(f"Update metadata files version in {x}")

                if question:
                    toml.dumps(version_old, encoder=None)
                    with open(
                        pathlib.Path(metadata_dir, x), "w", encoding="utf-8"
                    ) as text_file:
                        text_file.write(toml.dumps(version_old, encoder=None))
                    pathlib.Path(metadata_dir, x + ".temp").unlink()
                    print(
                        f"{x} updated from version {version_old_print} to version {version_new}!"
                    )
                else:
                    pathlib.Path(metadata_dir, x + ".temp").unlink()
                    print(
                        f"{x} was NOT updated from version {version_old_print} to version {version_new}!"
                    )
            else:
                pathlib.Path(metadata_dir, x + ".temp").unlink()
                print("Nothing to update!")
        return None


def rm_temp(pth: pathlib.Path, dryrun):
    """
    Remove all files and folders from temp folder
    that contains the downloaded metadata files
    """
    if dryrun:
        pass
    else:
        for child in pth.iterdir():
            if child.is_file():
                child.unlink()
            else:
                rm_temp(child, dryrun)
        pth.rmdir()
    return None


def user_response(question):
    """
    Function to evaluate the user response to the Yes or No question refarding updating
    the metadata files.
    """
    prompt = f"{question}? (y/n): "
    answer = input(prompt).strip().lower()
    pos = ["yes", "y", "yay"]
    neg = ["no", "n", "nay"]
    if not (answer in pos or answer in neg):
        print(f"That was a yes or no question, but you answered: {answer}")
        return user_response(question)
    if answer in pos:
        return True
    return False


def external_repo(project_dir, external, dryrun):
    """
    Function to evaluate the user response to the Yes or No question refarding updating
    the metadata files.
    """
    if dryrun:
        if external:
            metadata_dir = pathlib.Path(project_dir, "cubi")
        else:
            metadata_dir = project_dir
    else:
        if external:
            metadata_dir = pathlib.Path(project_dir, "cubi")
            metadata_dir.mkdir(parents=True, exist_ok=True)
        else:
            metadata_dir = project_dir
    return metadata_dir


def report_script_version():
    """
    Read out of the cubi-tools script version out of the 'pyproject.toml'.
    """
    toml_file = pathlib.Path(
        pathlib.Path(__file__).resolve().parent.parent, "pyproject.toml"
    )
    toml_file = toml.load(toml_file, _dict=dict)
    version = toml_file["cubi"]["tools"]["script"][0]["version"]
    return version


if __name__ == "__main__":
    main()
