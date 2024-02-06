#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import shutil
import hashlib
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
    print(f"Project directory set as: {project_dir}")

    ref_repo = args.ref_repo
    source = args.source
    external = args.external

    # Since using the online github repo directly to update the local metadata files
    # is resulting in hitting an API rate limit fairly quickly a local copy is needed.
    # The location of the template_metadata folder holding branch/version tag
    # of interest is on the same level as the project directory
    metadata_dir = pathlib.Path(
        pathlib.Path(f"{project_dir}").resolve().parents[0],
        "template-metadata-files",
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
    clone(workflow_dir, project_dir, ref_repo, source, metadata_dir, dryrun)

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

    # For 'git pull' you have to be in a branch of the template-metadata-files repo to
    # merge with. If you previously chose a version tag to update from, 'git pull' will
    # throw a waning message. This part will reset the repo to the main branch to avoid
    # any warning message stemming from 'git pull'
    command_reset = ["git", "checkout", "main", "-q"]
    sp.run(
        command_reset,
        cwd=metadata_dir,
        check=False,
    )

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
        "-p",
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


def clone(workflow_dir, project_dir, ref_repo, source, metadata_dir, dryrun):
    """
    Check if the 'template-metadata-files' repo is already parallel to the
    project directory. If the 'template-metadata-files' repo exists this folder is
    getting updated via a 'git pull --all' command. If that is not the case,
    the 'template-metadata-files' repo will be cloned parallel to the project
    directory unless the branch or version tag don't exist,
    then an AssertionError will be called to stop the script.
    """
    if dryrun:
        if not metadata_dir.is_dir():
            raise NameError(
                "The 'template-metadata-files' repo needs to be present in the "
                f"parental folder of the project directory {project_dir}.\n"
                "In a live run the 'template-metadata-files' repo would "
                f"be created at {metadata_dir}.\n"
            )
        else:
            print(
                "The requested branch/version tag (default: main) is present "
                "and is getting updated via 'git pull -all' .\n"
            )
            command = [
                "git",
                "pull",
                "--all",
                "-q",
            ]
            sp.run(
                command,
                cwd=metadata_dir,
                check=False,
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            checkout_cmd = sp.run(
                command_checkout,
                cwd=metadata_dir,
                stderr=sp.PIPE,
                check=False,
            )
            # If the 'template-metadata-files' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(checkout_cmd.stderr.strip()), (
                "The folder 'template-metadata-files' is not a git repository! "
                "For this script to work either delete the folder or move it!!"
            )
            # If you try to clone a repo/branch/tag that doesn't exist
            # Git will throw an error message that contains the string 'error:'
            error = "error:"
            assert error not in str(
                checkout_cmd.stderr.strip()
            ), f"The branch or version tag named '{source}' doesn't exist"
    else:
        if metadata_dir.is_dir():
            command = [
                "git",
                "pull",
                "--all",
                "-q",
            ]
            sp.run(
                command,
                cwd=metadata_dir,
                check=False,
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            checkout_cmd = sp.run(
                command_checkout,
                cwd=metadata_dir,
                stderr=sp.PIPE,
                check=False,
            )
            # If the 'template-metadata-files' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(checkout_cmd.stderr.strip()), (
                "The folder 'template-metadata-files' is not a git repository! "
                "For this script to work either delete the folder or move it!!"
            )
            # If you try to clone a repo/branch/tag that doesn't exist
            # Git will throw an error message that contains the string 'error:'
            error = "error:"
            assert error not in str(
                checkout_cmd.stderr.strip()
            ), f"The branch or version tag named '{source}' doesn't exist"
        else:
            command = [
                "git",
                "clone",
                "-q",
                "-c advice.detachedHead=false",
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
            # If the 'template-metadata-files' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(clone_cmd.stderr.strip()), (
                "The repository you entered or the branch or version tag "
                f"named '{source}' doesn't exist"
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            sp.run(
                command_checkout,
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
        local_sum = get_local_checksum(workflow_dir, f)
        ref_sum = get_ref_checksum(metadata_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            print(f"Update '{f}'(y/n)? y")
            print(f"Dry run! '{f}' would be updated!")
        else:
            print(f"Dry run! '{f}' is up-to-date!")
    else:
        local_sum = get_local_checksum(workflow_dir, f)
        ref_sum = get_ref_checksum(metadata_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            question = user_response(f"Update '{f}'")

            if question:
                shutil.copyfile(metadata_dir.joinpath(f), workflow_dir.joinpath(f))
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
    if dryrun:
        if not workflow_dir.joinpath("pyproject.toml").is_file():
            print(
                "\nThere is no 'pyproject.toml' in your folder. "
                "Do you want to add 'pyproject.toml'(y/n)? y"
                "\nDry run! 'pyproject.toml' would have been added!"
            )
        else:
            comparison = compare_metadata_versions(workflow_dir, metadata_dir)
            # Just to clearly state which information/files are generated by the
            # function 'compare_metadata_versions(workflow_dir, metadata_dir)':
            metadata_version = comparison[0]
            workflow_version = comparison[1]
            new_pyproject_toml = comparison[2]

            if metadata_version != workflow_version:
                print(
                    "\nYou updated your local repo with the 'template-metadata-files' "
                    f"in branch/version tag '{source}'."
                    "\nDo you want to update the metadata files version in "
                    "'pyproject.toml'(y/n)? y"
                )
                print(
                    "Dry run!\n"
                    "Metadata version in 'pyproject.toml' would have been updated from "
                    f"version '{workflow_version}' to version '{metadata_version}'!"
                )
            else:
                print(
                    "\nDry run! Metadata version in 'pyproject.toml' is up-to-date!\n"
                )
    else:
        if not workflow_dir.joinpath("pyproject.toml").is_file():
            question = user_response(
                "There is no 'pyproject.toml' in your folder. Add 'pyproject.toml'"
            )

            if question:
                shutil.copyfile(
                    metadata_dir.joinpath("pyproject.toml"),
                    workflow_dir.joinpath("pyproject.toml"),
                )
                print("'pyproject.toml' was added!")
            else:
                print("'pyproject.toml' was NOT added!")

        else:
            comparison = compare_metadata_versions(workflow_dir, metadata_dir)
            # Just to clearly state which information/files are generated by the
            # function 'compare_metadata_versions(workflow_dir, metadata_dir)':
            metadata_version = comparison[0]
            workflow_version = comparison[1]
            new_pyproject_toml = comparison[2]

            if metadata_version != workflow_version:
                question = user_response(
                    "\nYou updated your local repo with the 'template-metadata-files' "
                    f"in branch/version tag '{source}'."
                    "\nDo you want to update the metadata files version in "
                    "'pyproject.toml'"
                )

                if question:
                    with open(
                        pathlib.Path(workflow_dir, "pyproject.toml"),
                        "w",
                        encoding="utf-8",
                    ) as text_file:
                        text_file.write(toml.dumps(new_pyproject_toml, encoder=None))
                    print(
                        f"Metadata version in 'pyproject.toml' was updated from version"
                        f" '{workflow_version}' to version '{metadata_version}'!"
                    )
                else:
                    print(
                        "'pyproject.toml' was NOT updated from version "
                        f"'{workflow_version}' to version '{metadata_version}'!"
                    )
            else:
                print("\nMetadata version in 'pyproject.toml' is up-to-date!\n")
        return None


def user_response(question, attempt=0):
    """
    Function to evaluate the user response to the Yes or No question refarding updating
    the metadata files.
    """
    attempt += 1
    prompt = f"{question}? (y/n): "
    answer = input(prompt).strip().lower()
    pos = ["yes", "y", "yay"]
    neg = ["no", "n", "nay"]
    if attempt == 3:
        raise AttributeError("You failed 3 times to answer a simple (y/n) question!")
    else:
        if not (answer in pos or answer in neg):
            print(f"That was a yes or no question, but you answered: {answer}")
            return user_response(question, attempt)
    if answer in pos or answer in neg:
        return answer in pos


def compare_metadata_versions(workflow_dir, metadata_dir):
    """
    Function to compare the metadata version number in the pyproject.toml of
    the local repository with the metadata version of the pyproject.toml of
    the source 'template-metadata-files'.
    """
    # loading the pyproject.tomls:
    metadata_pyproject = toml.load(
        pathlib.Path(metadata_dir, "pyproject.toml"), _dict=dict
    )
    workflow_pyproject = toml.load(
        pathlib.Path(workflow_dir, "pyproject.toml"), _dict=dict
    )
    # extracting the metadata versions:
    metadata_version = metadata_pyproject["cubi"]["metadata"]["version"]
    workflow_version = workflow_pyproject["cubi"]["metadata"]["version"]
    # updating the metadata version in the workflow pyproject with the metadata version
    # from the template-metadata-files 'source' pyproject:
    workflow_pyproject["cubi"]["metadata"]["version"] = metadata_version

    return metadata_version, workflow_version, workflow_pyproject


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
