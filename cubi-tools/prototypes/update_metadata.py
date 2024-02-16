#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import shutil
import hashlib
import toml


def main():
    """
    Main function of the 'update-metadata.py' script.
    """

    args = parse_command_line()
    dryrun = args.dryrun

    # Is it a dry run?
    if dryrun:
        print("\nTHIS IS A DRY RUN!!")

    # check if project directory exist:
    working_dir = pathlib.Path(args.working_dir).resolve()
    if not working_dir.is_dir():
        raise FileNotFoundError(f"The project directory {working_dir} does not exist.")
    print(f"Project directory set as: {working_dir}")

    ref_repo = args.ref_repo
    branch = args.branch
    external = args.external


    # The location of the 'template-metadata-files" folder holding branch/version tag
    # needs to be parallel the project directory
    metadata_branch = pathlib.Path(
        pathlib.Path(f"{working_dir}").resolve().parents[0],
        "template-metadata-files",
    ).resolve()


    # detect if its a external workflow
    if external:
        metadata_target = define_metadata_target(working_dir, external, dryrun)
        print(f"\nExternal set as: {external}\n")
        print(
            "Metadata files will be updated in: "
            f"{define_metadata_target(working_dir, external, dryrun)}\n"
        )
    else:
        metadata_target = define_metadata_target(working_dir, external, dryrun)
        print(
            "\nMetadata files will be updated in: "
            f"{define_metadata_target(working_dir, external, dryrun)}\n"
        )

    # Clone the 'template-metadata-files' branch or version tag
    # into a local folder if it exists
    clone(metadata_target, working_dir, ref_repo, branch, metadata_branch, dryrun)

    # files that will be updated
    metadata_files = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
        "pyproject.toml",
    ]

    # Updating routine of the metadata files
    for file_to_update in metadata_files:
        if file_to_update == "pyproject.toml":
            update_pyproject_toml(metadata_target, metadata_branch, branch, dryrun)
        else:
            print(
                f"Comparing if local '{file_to_update}' differs from version in "
                f"branch/version tag '{branch}' in the 'template-metadata-files' repo"
            )
            update_file(metadata_target, metadata_branch, file_to_update, dryrun)

    # For 'git pull' you have to be in a branch of the template-metadata-files repo to
    # merge with. If you previously chose a version tag to update from, 'git pull' will
    # throw a waning message. This part will reset the repo to the main branch to avoid
    # any warning message stemming from 'git pull'
    command_reset = ["git", "checkout", "main", "-q"]
    sp.run(
        command_reset,
        cwd=metadata_branch,
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
        "Example: python3 add-update-metadata.py --update-dir path/to/repo"
    )
    parser.add_argument(
        "--working-dir",
        "-w",
        type=pathlib.Path,
        nargs="?",
        help="(Mandatory) Directory where metadata should be copied/updated.",
        required=True,
    )

    DEFAULT_REF_REPO = (
        "https://github.com/core-unit-bioinformatics/template-metadata-files.git"
    )
    parser.add_argument(
        "--ref-repo",
        type=str,
        nargs="?",
        default=DEFAULT_REF_REPO,
        help=f"Reference/remote repository used to clone files. Default: {DEFAULT_REF_REPO}",
    )
    parser.add_argument(
        "--external",
        "-e",
        action="store_true",
        default=False,
        dest="external",
        help="If False (default), metadata files are copied to the metadata_target, "
        "else to a subfolder (cubi). Default: False",
    )
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        nargs="?",
        default="main",
        help="Branch or version tag from which to update the files. Default: main",
    )
    parser.add_argument(
        "--dry-run",
        "--dryrun",
        "-d",
        "-dry",
        action="store_true",
        default=False,
        dest="dryrun",
        help="Just report actions but do not execute them. Default: False",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=report_script_version(),
        help="Displays version of this script.",
    )
    # if no arguments are given, print help
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()  # default is code 0
    args = parser.parse_args()
    return args


def clone(metadata_target, working_dir, ref_repo, branch, metadata_branch, dryrun):
    """
    Check if the 'template-metadata-files' repo is already parallel to the
    project directory. If the 'template-metadata-files' repo exists this folder is
    getting updated via a 'git pull --all' command. If that is not the case,
    the 'template-metadata-files' repo will be cloned parallel to the project
    directory unless the branch or version tag don't exist,
    then an AssertionError will be called to stop the script.
    """
    if dryrun:
        if not metadata_branch.is_dir():
            raise NameError(
                "The 'template-metadata-files' repo needs to be present "
                f"parallel to the project directory {working_dir}.\n"
                "In a live run the 'template-metadata-files' repo would "
                f"be created at {metadata_branch}.\n"
            )
        else:
            print(
                "The requested branch/version tag (default: main) is present "
                "and is getting updated via 'git pull -all' .\n"
            )
            git_pull_template(metadata_branch, branch)
    else:
        if metadata_branch.is_dir():
            git_pull_template(metadata_branch, branch)
        else:
            git_clone_template(ref_repo, metadata_branch, metadata_target, branch)
    return None


def calculate_md5_checksum(file_path):
    """
    The MD5 checksum for the metadata files of the local folder or
    for the template-metadata branch or version tag is determined.

    Args:
        file_path (pathlib.Path): either the path to metadata_target or metadata_branch
        file_to_update (list): metadata files to update

    Returns:
        md5_hash: MD5 checksum of metadata file
    """
    if file_path.is_file():
        with open(file_path, "rb") as metadata_file:
            data = metadata_file.read()
            md5_hash = hashlib.md5(data).hexdigest()
    else:
        md5_hash = ""
    return md5_hash

def update_file(metadata_target, metadata_branch, file_to_update, dryrun):
    """_summary_

    Args:
        metadata_target (pathlib.Path):
            The folder being processed / receiving the metadata update
        metadata_branch (pathlib.Path):
            The branch folder of the update process, i.e., that should
            almost always refer to 'template-metadata-files'
    """
    metadata_target_file = metadata_target.joinpath(file_to_update)
    metadata_branch_file = metadata_branch.joinpath(file_to_update)
    md5_local = calculate_md5_checksum(metadata_target_file)
    md5_ref = calculate_md5_checksum(metadata_branch_file)

    if md5_local != md5_ref:
        if dryrun:
            print(f"The versions of '{file_to_update}' differ!")
            print(f"Local MD5 checksum: {md5_local}")
            print(f"Remote MD5 checksum: {md5_ref}")
            print(f"Update '{file_to_update}'(y/n)? y")
            print(f"Dry run! '{file_to_update}' would be updated!")
        else:
            print(f"The versions of '{file_to_update}' differ!")
            print(f"Local MD5 checksum: {md5_local}")
            print(f"Remote MD5 checksum: {md5_ref}")
            answer_is_pos = user_response(f"Update '{file_to_update}'")

            if answer_is_pos:
                shutil.copyfile(metadata_branch.joinpath(file_to_update),
                                metadata_target.joinpath(file_to_update)
                            )
                print(f"'{file_to_update}' was updated!")
            else:
                print(f"'{file_to_update}' was NOT updated!")
    else:
        print(f"'{file_to_update}' is up-to-date!")
    return None


def update_pyproject_toml(metadata_target, metadata_branch, branch, dryrun):
    """
    The 'pyproject.toml' is treated a little bit differently. First, there is
    a check if the file even exists in the project directory. If that is not the
    case it will be copied into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.metadata.version
    (and only that information!) differs between the local and the requested branch
    or version tag version. If that is the case the cubi.metadata.version
    is getting updated.
    """

    if not metadata_target.joinpath("pyproject.toml").is_file():
        if dryrun:
            print(
                "\nThere is no 'pyproject.toml' in your folder. "
                "Do you want to add 'pyproject.toml'(y/n)? y"
                "\nDry run! 'pyproject.toml' would have been added!"
            )
        else:
            answer_is_pos = user_response(
                "There is no 'pyproject.toml' in your folder. Add 'pyproject.toml'"
            )

            if answer_is_pos:
                shutil.copyfile(
                    metadata_branch.joinpath("pyproject.toml"),
                    metadata_target.joinpath("pyproject.toml"),
                )
                print("'pyproject.toml' was added!")
            else:
                print("'pyproject.toml' was NOT added!")
    else:
        metadata_version = get_metadata_versions(metadata_branch, metadata_target)
        # Just to clearly state which information/files are generated by the
        # function 'get_metadata_versions(metadata_branch, metadata_target)':
        branch_version = metadata_version[0]    # Metadata version of the branch (str)
        target_version = metadata_version[1]    # Metadata version of the target (str)
        target_pyproject = metadata_version[2]  # Target pyproject toml w/ updated metadata version (dict)

        if branch_version != target_version:
            if dryrun:
                print(
                    "\nYou updated your local repo with the 'template-metadata-files' "
                    f"in branch/version tag '{branch}'."
                    "\nDo you want to update the metadata files version in "
                    "'pyproject.toml'(y/n)? y"
                )
                print(
                    "Dry run!\n"
                    "Metadata version in 'pyproject.toml' would have been updated from "
                    f"version '{target_version}' to version '{branch_version}'!"
                )
            else:
                answer_is_pos = user_response(
                    "\nYou updated your local repo with the 'template-metadata-files' "
                    f"in branch/version tag '{branch}'."
                    "\nDo you want to update the metadata files version in "
                    "'pyproject.toml'"
                )

                if answer_is_pos:
                    with open(
                        pathlib.Path(metadata_target, "pyproject.toml"),
                        "w",
                        encoding="utf-8",
                    ) as text_file:
                        text_file.write(toml.dumps(target_pyproject, encoder=None))
                    print(
                        f"Metadata version in 'pyproject.toml' was updated from version"
                        f" '{branch_version}' to version '{target_version}'!"
                    )
                else:
                    print(
                        "'pyproject.toml' was NOT updated from version "
                        f"'{branch_version}' to version '{target_version}'!"
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
    if attempt >= 3:
        raise RuntimeError(
            "You failed at least 3 times to answer a simple (y/n) question!"
        )

    if not (answer in pos or answer in neg):
        print(f"That was a yes or no question, but you answered: {answer}")
        return user_response(question, attempt)
    return answer in pos


def get_metadata_versions(metadata_branch, metadata_target):
    """Read the metadata version strings in the respective
    pyproject.toml files from the metadata branch and target
    directories.

    Args:
        metadata_target (pathlib.Path):
            The folder being processed / receiving the metadata update
        metadata_branch (pathlib.Path):
            The branch folder of the update process, i.e., that should
            almost always refer to 'template-metadata-files'

    Returns:
        str: Metadata version of the branch
        str: Metadata version of the target
        dict: Target pyproject toml w/ updated metadata version
    """
    # loading the pyproject.tomls:
    branch_pyproject = toml.load(
        pathlib.Path(metadata_branch, "pyproject.toml"), _dict=dict
    )
    target_pyproject = toml.load(
        pathlib.Path(metadata_target, "pyproject.toml"), _dict=dict
    )
    # extracting the metadata versions:
    branch_version = branch_pyproject["cubi"]["metadata"]["version"]
    target_version = target_pyproject["cubi"]["metadata"]["version"]
    # updating the metadata version in the workflow pyproject with the metadata version
    # from the template-metadata-files 'branch' pyproject:
    target_pyproject["cubi"]["metadata"]["version"] = branch_version

    return branch_version, target_version, target_pyproject


def define_metadata_target(working_dir, external, dryrun):
    """
    Function to create a 'cubi' folder where the CUBI metadata files will be
    copied/updated if the user stated that the project is from external.
    Otherwise use given working directory.
    """
    if dryrun:
        if external:
            metadata_target = pathlib.Path(working_dir, "cubi")
        else:
            metadata_target = working_dir
    else:
        if external:
            metadata_target = pathlib.Path(working_dir, "cubi")
            metadata_target.mkdir(parents=True, exist_ok=True)
        else:
            metadata_target = working_dir
    return metadata_target


def find_cubi_tools_top_level():
    """Find the top-level folder of the cubi-tools
    repository (starting from this script path).
    """
    script_path = pathlib.Path(__file__).resolve(strict=True)
    script_folder = script_path.parent

    cmd = ["git", "rev-parse", "--show-toplevel"]
    repo_path = sp.check_output(cmd, cwd=script_folder).decode("utf-8").strip()
    repo_path = pathlib.Path(repo_path)
    return repo_path


def report_script_version():
    """
    Read out of the cubi-tools script version out of the 'pyproject.toml'.
    """
    cubi_tools_repo = find_cubi_tools_top_level()

    toml_file = cubi_tools_repo.joinpath("pyproject.toml").resolve(strict=True)

    toml_file = toml.load(toml_file, _dict=dict)
    version = toml_file["cubi"]["tools"]["script"][0]["version"]
    return version


def git_pull_template(metadata_branch, branch):
    """
    This function will pull updates from the remote template repository.
    """
    command = [
        "git",
        "pull",
        "--all",
        "-q",
    ]
    sp.run(
        command,
        cwd=metadata_branch,
        check=False,
    )
    command_checkout = ["git", "checkout", "".join({branch}), "-q"]
    checkout_cmd = sp.run(
        command_checkout,
        cwd=metadata_branch,
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
    ), f"The branch or version tag named '{branch}' doesn't exist"
    return None


def git_clone_template(ref_repo, metadata_branch, metadata_target, branch):
    """
    This function will clone the template repository into a folder parallel
    to the folder to get updated.
    """
    command = [
        "git",
        "clone",
        "-q",
        "-c advice.detachedHead=false",
        ref_repo,
        metadata_branch,
    ]
    clone_cmd = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        cwd=metadata_target,
        check=False,
    )
    # If the 'template-metadata-files' folder is not a Git repo
    # an error message that contains the string 'fatal:' will be thrown
    warning = "fatal:"
    assert warning not in str(clone_cmd.stderr.strip()), (
        "The repository you entered or the branch or version tag "
        f"named '{branch}' doesn't exist"
    )
    command_checkout = ["git", "checkout", "".join({branch}), "-q"]
    sp.run(
        command_checkout,
        cwd=metadata_branch,
        check=False,
    )
    return None

if __name__ == "__main__":
    main()
