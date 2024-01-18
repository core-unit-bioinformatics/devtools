#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import hashlib
import shutil
import toml


sys.tracebacklimit = -1


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

    # check if project directory exist:
    project_dir = pathlib.Path(args.project_dir).resolve()
    assert project_dir.is_dir(), f"The project directory {project_dir} doesn't exist!"
    print(f"Project directory set as: {project_dir}\n")

    ref_repo = args.ref_repo
    source = args.source
    external = args.external
    keep = args.keep

    # Since using the online github repo directly to update the local metadata files
    # is resulting in hitting an API rate limit fairly quickly a local copy is needed.
    # The location of the template_metadata folder holding branch/version tag
    # of interest is on the same level as the project directory
    metadata_dir = pathlib.Path(
        pathlib.Path(f"{project_dir}").resolve().parents[0],
        f"update_metadata_temp/{source}",
    ).resolve()

    # detect if its a external workflow
    if external:
        workflow_dir = external_repo(project_dir, external, dryrun)
        print(f"\nExternal set as: {external}\n")
        print(
            "Metadata files will be updated in: "
            f"{external_repo(project_dir, external, dryrun)}\n"
        )
    else:
        workflow_dir = external_repo(project_dir, external, dryrun)
        print(
            "\nMetadata files will be updated in: "
            f"{external_repo(project_dir, external, dryrun)}\n"
        )

    # Clone the 'template-metadata-files' branch or version tag
    # into a local folder if it exists
    clone(project_dir, ref_repo, source, metadata_dir, dryrun)

    # files that will be updated
    files_to_update = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
        "pyproject.toml",
    ]

    # Updating routine of the metadata files
    for f in files_to_update:
        if f == "pyproject.toml":
            update_pyproject_toml(workflow_dir, metadata_dir, source, dryrun)
        else:
            print(
                f"Comparing if local '{f}' differs from version in branch/version tag "
                f"'{source}' in the 'template-metadata-files' repo"
            )
            update_file(f, workflow_dir, metadata_dir, dryrun)

    # detect if metafiles temp folder should be kept
    if keep:
        print(
            f"\nYou want to keep the files of the branch/version tag '{source}' "
            "of the 'template-metadata-files' folder.\n"
            f"It's located at '{metadata_dir}'"
        )
    else:
        rm_temp(metadata_dir.parent, dryrun)
        # print("\nThe 'update_metadata_temp' folder with all files
        # and subfolders has been deleted!")

    print("\nUPDATE COMPLETED!")

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
        "-e",
        action="store_true",
        default=False,
        dest="external",
        help="If False (default), metadata files are copied to the project_dir, "
        "else to a subfolder (cubi).",
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        nargs="?",
        default="main",
        help="Branch or version tag from which to update the files",
    )
    parser.add_argument(
        "--keep",
        "-k",
        action="store_true",
        default=False,
        dest="keep",
        help="If False (default), the metadata files source repo "
        "will be deleted when script finishes else it will be kept.",
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
        "-v",
        action="store_true",
        help="Displays version of this script.",
    )
    # if no arguments are given, print help
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()  # default is code 0
    args = parser.parse_args()
    return args


def clone(workflow_dir, ref_repo, source, metadata_dir, dryrun):
    """
    Check if the branch or version tag that contains the desired metadata files
    is already in a temp folder parallel to the project directory.
    If that is not the case, the desired branch or version tag will be cloned into
    a temp folder parallel to the project directory unless the branch or version tag
    don't exist, then an AssertionError will be called to stop the script.
    If a temp folder for the branch or version tag exists this folder is getting
    updated via a git pull command.
    """
    if dryrun:
        if not metadata_dir.is_dir():
            print(
                "The requested branch/version tag (default: main) is being "
                f"copied to {metadata_dir}.\n"
            )
        else:
            print(
                "The requested branch/version tag (default: main) already "
                "exists and is getting updated.\n"
            )
    else:
        if not metadata_dir.is_dir():
            command = [
                "git",
                "clone",
                "-q",
                "-c advice.detachedHead=false",
                "--depth=1",  # depth =1 to avoid big .git file
                "--branch",
                source,
                ref_repo,
                metadata_dir,
            ]
            clone_cmd = sp.run(
                command,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                cwd=workflow_dir,
                check=False,
            )
            # Git will throw a error message if you try to clone a repo/branch/tag
            # that doesn't exist that contains the string 'fatal:'
            warning = "fatal:"
            assert warning not in str(clone_cmd.stderr.strip()), (
                "The repository you entered or the branch or version tag "
                f"named '{source}' doesn't exist"
            )
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
                cwd=metadata_dir,
                check=False,
            )
    return None


def get_local_checksum(workflow_dir, f):
    """
    The MD5 checksum for all metadata files in the
    local project directory is determined.
    """
    if workflow_dir.joinpath(f).is_file():
        with open(workflow_dir.joinpath(f), "rb") as local_file:
            # read contents of the file
            local_data = local_file.read()
            # pipe contents of the file through
            md5_local = hashlib.md5(local_data).hexdigest()
    else:
        md5_local = ""
    return md5_local


def get_ref_checksum(metadata_dir, f):
    """
    The MD5 checksum for all metadata files in the temp folder
    for the desired branch or version tag is determined.
    """
    with open(metadata_dir.joinpath(f), "rb") as ref_file:
        # read contents of the file
        ref_data = ref_file.read()
        # pipe contents of the file through
        md5_ref = hashlib.md5(ref_data).hexdigest()
    return md5_ref


def update_file(f, workflow_dir, metadata_dir, dryrun):
    """
    The MD5 checksum of the the local metadata file(s) and the metadata
    file(s) in the desired branch or version tag are being compared.
    If they differ a question to update for each different
    metadata file pops up. If an update is requested it will be performed.
    """
    if dryrun:
        print(f"The versions of '{f}' differ!")
        print("Local MD5 checksum: (some MD5 checksum)")
        print("Remote MD5 checksum: (some other MD5 checksum)")
        print(f"Update '{f}'(y/n)? y")
        print(f"Dry run! '{f}' would be updated!")
    else:
        local_sum = get_local_checksum(workflow_dir, f)
        ref_sum = get_ref_checksum(metadata_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            question = user_response(f"Update '{f}'")

            if question:
                command = [
                    "cp",
                    metadata_dir.joinpath(f),
                    workflow_dir.joinpath(f),
                ]
                sp.run(command, cwd=workflow_dir, check=False)
                print(f"'{f}' was updated!")
            else:
                print(f"'{f}' was NOT updated!")
        else:
            print(f"'{f}' is up-to-date!")
        return None


def update_pyproject_toml(workflow_dir, metadata_dir, source, dryrun):
    """
    The 'pyproject.toml' is treated a little bit differently. First, there is
    a check if the file even exists in the project directory. If that is not the
    case it will be copied into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.metadata.version
    (and only that information!) differs between the local and the requested branch
    or version tag version. If that is the case the cubi.metadata.version
    is getting updated.
    """
    x = "pyproject.toml"
    if dryrun:
        print(f"\nThere is no 'pyproject.toml' in your folder. Add '{x}'(y/n)? y")
        print(f"Dry run! '{x}' would have been added!")
        print(
            "\nYou updated your local repo with the 'template-metadata-files' "
            f"in branch/version tag '{source}'."
            f"\nDo you want to update the metadata files version in '{x}'(y/n)? y"
        )
        print(
            f"Dry run! Metadata version in '{x}' would have been updated from version "
            "'v1' to version 'v2'!"
        )
    else:
        if not workflow_dir.joinpath(x).is_file():
            question = user_response(
                f"There is no 'pyproject.toml' in your folder. Add '{x}'"
            )

            if question:
                command = [
                    "cp",
                    metadata_dir.joinpath(x),
                    workflow_dir.joinpath(x),
                ]
                sp.run(command, cwd=workflow_dir, check=False)
                print(f"'{x}' was added!")
            else:
                print(f"'{x}' was NOT added!")

        else:
            command = [
                "cp",
                metadata_dir.joinpath(x),
                pathlib.Path(workflow_dir, x + ".temp"),
            ]
            sp.run(command, cwd=workflow_dir, check=False)
            version_new = toml.load(pathlib.Path(workflow_dir, x + ".temp"), _dict=dict)
            version_old = toml.load(pathlib.Path(workflow_dir, x), _dict=dict)
            version_new = version_new["cubi"]["metadata"]["version"]
            version_old_print = version_old["cubi"]["metadata"]["version"]
            version_old["cubi"]["metadata"]["version"] = version_new

            if version_old_print != version_new:
                question = user_response(
                    "\nYou updated your local repo with the 'template-metadata-files' "
                    f"in branch/version tag '{source}'."
                    f"\nDo you want to update the metadata files version in '{x}'"
                )

                if question:
                    toml.dumps(version_old, encoder=None)
                    with open(
                        pathlib.Path(workflow_dir, x), "w", encoding="utf-8"
                    ) as text_file:
                        text_file.write(toml.dumps(version_old, encoder=None))
                    pathlib.Path(workflow_dir, x + ".temp").unlink()
                    print(
                        f"Metadata version in '{x}' was updated from version "
                        f"'{version_old_print}' to version '{version_new}'!"
                    )
                else:
                    pathlib.Path(workflow_dir, x + ".temp").unlink()
                    print(
                        f"'{x}' was NOT updated from version '{version_old_print}' "
                        f"to version '{version_new}'!"
                    )
            else:
                pathlib.Path(workflow_dir, x + ".temp").unlink()
                print(f"\nMetadata version in '{x}' is up-to-date!\n")
        return None


def rm_temp(pth: pathlib.Path, dryrun):
    """
    Remove all files and folders from update_metadata_temp folder
    that contains the downloaded metadata files
    """
    if dryrun:
        pass
    else:
        shutil.rmtree(pth)
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
    Function to create a cubi folder where the CUBI metadata files will be
    copied/updated if the user stated that the project is from external.
    """
    if dryrun:
        if external:
            workflow_dir = pathlib.Path(project_dir, "cubi")
        else:
            workflow_dir = project_dir
    else:
        if external:
            workflow_dir = pathlib.Path(project_dir, "cubi")
            workflow_dir.mkdir(parents=True, exist_ok=True)
        else:
            workflow_dir = project_dir
    return workflow_dir


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
