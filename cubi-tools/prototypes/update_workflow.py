#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import os
import shutil
import hashlib
import toml


__prog__ = "update_workflow.py"


def main():
    """
    Main function of the 'update-workflow.py' script.
    """

    args = parse_command_line()
    dryrun = args.dryrun

    # Is it a dry run?
    if dryrun:
        print("\nTHIS IS A DRY RUN!!")

    # check if project directory exist:
    workflow_target = pathlib.Path(args.workflow_dir).resolve()
    if not workflow_target.is_dir():
        raise FileNotFoundError(
            f"The project directory {workflow_target} doesn't exist!"
        )
    print(f"Project directory set as: {workflow_target}\n")

    ref_repo = args.ref_repo
    branch = args.branch
    metadata = args.metadata

    # The location of the 'template-snakemake" folder holding branch/version tag
    # needs to be parallel the project directory or provided via '--ref-repo'.
    if ref_repo != DEFAULT_REF_REPO:
        workflow_branch = pathlib.Path(args.ref_repo).resolve()
        if not workflow_branch.is_dir():
            raise FileNotFoundError(
                f"The reference directory {workflow_branch} does not exist."
            )
        print(f"Reference directory set as: {workflow_branch}")
    else:
        workflow_branch = pathlib.Path(
            pathlib.Path(f"{workflow_target}").resolve().parents[0],
            "template-snakemake",
        ).resolve()
        print(f"Reference directory set as: {workflow_branch}")

    # detect if workflow is based on CUBI's template_snakemake repo
    # The file '/workflow/rules/commons/10_constants.smk' should be present
    # if template_snakemake was used to create project folder
    if (
        not pathlib.Path(workflow_target)
        .joinpath("workflow", "rules", "commons", "10_constants.smk")
        .is_file()
    ):
        answer_is_pos = user_response(
            "ARE YOU SURE THIS PROJECT IS BASED ON CUBI'S "
            "'template_snakemake' REPOSITORY"
        )
        if not answer_is_pos:
            raise SystemExit(
                "This project is not based on CUBI's 'template_snakemake'. "
                "No changes have been made!"
            )

    # Clone/update the 'template-snakemake' repo
    # into a local folder if it exists
    clone(workflow_target, ref_repo, branch, workflow_branch, dryrun)

    # Call function to create the list of files and folders that
    # should be made/copied/updated:
    # Function creates tuple with 2 entries:
    # [0] = files to be updated
    # [1] = subfolders present in workflow branch
    update_information = update_file_list(workflow_branch, metadata, dryrun)

    dirs_to_make = [
        workflow_target / dir_path.relative_to(workflow_branch)
        for dir_path in update_information[1]
    ]

    for directories in dirs_to_make:
        os.makedirs(directories, exist_ok=True)

    # Updating routine of the metadata files
    for file_to_update in update_information[0]:
        if file_to_update == "pyproject.toml":
            update_pyproject_toml(workflow_target, workflow_branch, branch, dryrun)
        else:
            print(
                f"Comparing if local '{file_to_update}' differs from version in "
                f"branch/version tag '{branch}' in the 'template-snakemake' repo"
            )
            update_file(workflow_target, workflow_branch, file_to_update, dryrun)

    # For 'git pull' you have to be in a branch of the template-snakemake repo to
    # merge with. If you previously chose a version tag to update from, 'git pull' will
    # throw a waning message. This part will reset the repo to the main branch to avoid
    # any warning message stemming from 'git pull'
    command_reset = ["git", "checkout", "main", "-q"]
    sp.run(
        command_reset,
        cwd=workflow_branch,
        check=False,
    )

    print("\nUPDATE COMPLETED!")

    return None


def parse_command_line():
    """
    Collection of the various options of the 'update-workflow.py' script.
    """
    parser = argp.ArgumentParser(
        prog=__prog__,
        description="Add or update workflow files for your repository. "
        "Example: python3 update_workflow.py --workflow-dir path/to/repo",
    )
    parser.add_argument(
        "--workflow_dir",
        "-w",
        type=pathlib.Path,
        help="(Mandatory) Directory where workflow template files "
        "should be copied/updated.",
        required=True,
    )
    global DEFAULT_REF_REPO
    DEFAULT_REF_REPO = (
        "https://github.com/core-unit-bioinformatics/template-snakemake.git"
    )
    parser.add_argument(
        "--ref-repo",
        type=str,
        nargs="?",
        default=DEFAULT_REF_REPO,
        help="Reference/remote repository used to clone files. "
        f"Default: {DEFAULT_REF_REPO}",
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
        "--metadata",
        "-m",
        action="store_true",
        default=False,
        dest="metadata",
        help="Also metadata files will be updated. Default: False",
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


def clone(workflow_target, ref_repo, branch, workflow_branch, dryrun):
    """
    Check if the 'template-snakemake' repo is already parallel to the
    project directory. If the 'template-snakemake' repo exists this folder is
    getting updated via a 'git pull --all' command. If that is not the case,
    the 'template-snakemake' repo will be cloned parallel to the project
    directory unless the branch or version tag don't exist,
    then an FileNotFoundError will be called to stop the script.
    """
    if dryrun:
        if not workflow_branch.is_dir():
            raise FileNotFoundError(
                "For default usage the 'template-metadata-files' repo needs to be "
                f"present parallel to the project directory {workflow_target}.\n"
                "If you provided a local location via the '--ref-repo' option make sure"
                " it's present and a git repository."
            )
        else:
            print(
                "The requested branch/version tag (default: main) is present "
                "and is getting updated via 'git pull -all' .\n"
            )
            git_pull_template(workflow_branch, branch)
    else:
        if workflow_branch.is_dir():
            git_pull_template(workflow_branch, branch)
        else:
            git_clone_template(ref_repo, workflow_branch, workflow_target, branch)
    return None


def git_pull_template(workflow_branch, branch):
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
        cwd=workflow_branch,
        check=False,
    )
    command_checkout = ["git", "checkout", "".join({branch}), "-q"]
    checkout_cmd = sp.run(
        command_checkout,
        cwd=workflow_branch,
        stderr=sp.PIPE,
        check=False,
    )
    # If the 'template-metadata-files' folder is not a Git repo
    # an error message that contains the string 'fatal:' will be thrown
    warning = "fatal:"
    if warning in str(checkout_cmd.stderr.strip()):
        raise FileNotFoundError(
            f"The folder {workflow_branch} is not a git repository! "
            "If you provided the location via the '--ref-repo' option make sure "
            "it's a git repository or don't use the '--ref-repo' option. \n"
            "Otherwise delete/move the 'template-snakemake' folder, which is "
            "located parallel to the repository that is getting updated and rerun!!"
        )
    # If you try to clone a repo/branch/tag that doesn't exist
    # Git will throw an error message that contains the string 'error:'
    error = "error:"
    if error in str(checkout_cmd.stderr.strip()):
        raise FileNotFoundError(
            f"The branch or version tag named '{branch}' doesn't exist"
        )
    return None


def git_clone_template(ref_repo, workflow_branch, workflow_target, branch):
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
        workflow_branch,
    ]
    clone_cmd = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        cwd=workflow_target,
        check=False,
    )
    # If the 'template-metadata-files' folder is not a Git repo
    # an error message that contains the string 'fatal:' will be thrown
    warning = "fatal:"
    if warning in str(clone_cmd.stderr.strip()):
        raise FileNotFoundError(
            "The repository or folder you entered or the branch or version tag "
            f"named '{branch}' doesn't exist"
        )
    command_checkout = ["git", "checkout", "".join({branch}), "-q"]
    sp.run(
        command_checkout,
        cwd=workflow_branch,
        check=False,
    )
    return None


def calculate_md5_checksum(file_path):
    """
    The MD5 checksum for all files of the local folder or
    for the template-snakemake branch or version tag is determined.

    Args:
        file_path (pathlib.Path): either the path to workflow_target or workflow_branch
        file_to_update (list): files to update

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


def update_file(workflow_target, workflow_branch, file_to_update, dryrun):
    """
    The MD5 checksum of the the local workflow file(s) and the template_snakemake
    file(s) in the desired branch or version tag are being compared.
    If they differ a question to update for each different
    workflow file pops up. If an update is requested it will be performed.

    Args:
        workflow_target (pathlib.Path):
            The folder being processed / receiving the update
        workflow_branch (pathlib.Path):
            The branch folder of the update process, i.e., that should
            almost always refer to 'template-snakemake'
    """
    workflow_target_file = workflow_target.joinpath(file_to_update)
    workflow_branch_file = workflow_branch.joinpath(file_to_update)
    md5_local = calculate_md5_checksum(workflow_target_file)
    md5_ref = calculate_md5_checksum(workflow_branch_file)

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
                shutil.copyfile(
                    workflow_branch.joinpath(file_to_update),
                    workflow_target.joinpath(file_to_update),
                )
                print(f"'{file_to_update}' was updated!")
            else:
                print(f"'{file_to_update}' was NOT updated!")
    else:
        print(f"'{file_to_update}' is up-to-date!")
    return None


def update_pyproject_toml(workflow_target, workflow_branch, branch, dryrun):
    """
    The 'pyproject.toml' is treated a little bit differently. First, there is
    a check if the file even exists in the project directory. If that is not the
    case it will be copied into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.workflow.template.version
    (and only that information!) differs between the local and the requested branch
    or version tag version. If that is the case the cubi.workflow.template.version
    is getting updated. If the 'metadata' switch is set also the cubi.metadata.version
    will be updated (if necessary).
    """
    if not workflow_target.joinpath("pyproject.toml").is_file():
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
                    workflow_branch.joinpath("pyproject.toml"),
                    workflow_target.joinpath("pyproject.toml"),
                )
                print("'pyproject.toml' was added!")
            else:
                print("'pyproject.toml' was NOT added!")
    else:
        pyproject_versions = get_pyproject_versions(workflow_target, workflow_branch)
        # Just to clearly state which information/files are generated by the
        # function 'get_metadata_versions(metadata_branch, metadata_target)':

        # Metadata version of the branch (str):
        branch_metadata_version = pyproject_versions[0]
        # Metadata version of the target (str):
        target_metadata_version = pyproject_versions[1]
        # Target pyproject toml w/ updated metadata version (dict):
        branch_workflow_version = pyproject_versions[2]
        target_workflow_version = pyproject_versions[3]
        target_pyproject = pyproject_versions[4]

        if (
            branch_metadata_version != target_metadata_version
            or branch_workflow_version != target_workflow_version
        ):
            if dryrun:
                print(
                    "\nYou updated your local repo with the 'template-snakemake' "
                    f"in branch/version tag '{branch}'."
                    "\nDo you want to update the workflow version in "
                    "'pyproject.toml'(y/n)? y"
                )
                print(
                    "Dry run!\n"
                    "\nMetadata version in 'pyproject.toml' would have been updated "
                    f"from version '{target_metadata_version}' to version "
                    f"'{branch_metadata_version}'! and "
                    "\nWorkflow version in 'pyproject.toml' would have been updated "
                    f"from version '{target_workflow_version}' to version "
                    f"'{branch_workflow_version}'!"
                )
            else:
                answer_is_pos = user_response(
                    "\nYou updated your local repo with the 'template-snakemake' "
                    f"in branch/version tag '{branch}'."
                    "\nDo you want to update the workflow version in "
                    "'pyproject.toml'"
                )

                if answer_is_pos:
                    with open(
                        pathlib.Path(workflow_target, "pyproject.toml"),
                        "w",
                        encoding="utf-8",
                    ) as text_file:
                        text_file.write(toml.dumps(target_pyproject, encoder=None))
                    print(
                        "\nMetadata version in 'pyproject.toml' was updated from "
                        f"version '{target_metadata_version}' to version "
                        f"'{branch_metadata_version}'! and "
                        "\nWorkflow version in 'pyproject.toml' was updated from "
                        f"version '{target_workflow_version}' to version "
                        f"'{branch_workflow_version}'!"
                    )
                else:
                    print(
                        "The 'pyproject.toml' metadata version was NOT updated from "
                        f"version '{target_metadata_version}' to version "
                        f"'{branch_metadata_version}' and "
                        "The 'pyproject.toml' workflow version was NOT updated from "
                        f"version '{target_workflow_version}' to version "
                        f"'{branch_workflow_version}'!"
                    )
        else:
            print(
                "\nMetadata and workflow versions in 'pyproject.toml' are "
                "up-to-date!\n"
            )
    return None


def user_response(question, attempt=0):
    """
    Function to evaluate the user response to the Yes or No question regarding updating
    the metadata files.
    """
    attempt += 1
    prompt = f"{question}? (y/n): "
    answer = input(prompt).strip().lower()
    pos = ["yes", "y", "yay"]
    neg = ["no", "n", "nay"]
    if not (answer in pos or answer in neg):
        print(f"That was a yes or no question, but you answered: {answer}")
        return user_response(question, attempt)
    if attempt == 2:
        print("YOU HAVE ONE LAST CHANCE TO ANSWER THIS (y/n) QUESTION!")
    if attempt >= 3:
        raise RuntimeError(
            "I warned you! You failed 3 times to answer a simple (y/n)"
            " question! Please start over!"
        )
    return answer in pos


def find_all_subdir_in_branch(workflow_branch):
    """
    Function to list all subdirectories in the 'template_snakemake' repo
    to be able to create all missing subfolders that doesn't belong to the
    ".git/ .
    """
    word_to_filter = ".git"

    subfolders = [
        subdir
        for subdir in workflow_branch.rglob("*")
        if subdir.is_dir()
        if word_to_filter not in subdir.parts
    ]

    return subfolders


def update_file_list(workflow_branch, metadata, dryrun):
    """
    Function to create a list of files that will be updated.
    """
    files_to_update = []

    # the following files need to be excluded because they are always project specific
    excluded_files = [
        "pyproject.toml",
        "workflow/rules/00_modules.smk",
        "workflow/rules/99_aggregate.smk",
    ]

    # create a list of all files in 'template_snakemake' directory without the excluded
    # files and the '.git' folder
    workflow_files = []
    for file in workflow_branch.rglob("*"):
        if file.is_file():
            workflow_files.append(str(pathlib.Path(file).relative_to(workflow_branch)))
            for item in workflow_files[:]:
                if item in excluded_files or ".git/" in item:
                    workflow_files.remove(item)

    # I want the 'pyproject.toml' file at the end of the list and therefore I excluded
    # it initially from the list and now I append it so it will be at the end
    workflow_files.append("pyproject.toml")

    subfolders = find_all_subdir_in_branch(workflow_branch)

    # metadata files
    metadata_files = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
    ]
    if dryrun:
        if metadata:
            files_to_update = [
                "LICENSE",
                "workflow/rules/commons/00_commons.smk",
                "pyproject.toml",
            ]
            print(
                "All workflow files incl. metadata files would be copied/updated!\n"
                "Only a small selection of files will be used for the dry run!\n"
            )
        else:
            files_to_update = [
                "README.md",
                "workflow/rules/commons/00_commons.smk",
                "pyproject.toml",
            ]
            print(
                "Just the workflow files without the metadata files would "
                "be copied/updated!\n"
                "Only a small selection of files will be used for the dry run!\n"
            )
    else:
        if metadata:
            files_to_update = workflow_files
        else:
            files_to_update = [
                item for item in workflow_files if item not in metadata_files
            ]
    return files_to_update, subfolders


def get_pyproject_versions(workflow_target, workflow_branch):
    """
    Read the metadata and workflow version strings in the respective
    pyproject.toml files from the template branch and target
    directories.

    Args:
        workflow_target (pathlib.Path):
            The folder being processed / receiving the workflow update
        workflow_branch (pathlib.Path):
            The branch folder of the update process, i.e., that should
            almost always refer to 'template-snakefile'

    Returns:
        Metadata version of the branch (str)
        Metadata version of the target (str)
        Workflow version of the branch (str)
        Workflow version of the target (str)
        Target pyproject toml w/ updated metadata and workflow version (dict)
    """
    # loading the pyproject.tomls:
    branch_pyproject = toml.load(
        pathlib.Path(workflow_branch, "pyproject.toml"), _dict=dict
    )
    target_pyproject = toml.load(
        pathlib.Path(workflow_target, "pyproject.toml"), _dict=dict
    )
    # extracting the metadata versions:
    branch_metadata_version = branch_pyproject["cubi"]["metadata"]["version"]
    target_metadata_version = target_pyproject["cubi"]["metadata"]["version"]
    # updating the metadata version in the workflow pyproject with the metadata version
    # from the template_snakemake 'source' pyproject:
    target_pyproject["cubi"]["metadata"]["version"] = branch_metadata_version

    # extracting the workflow versions:
    branch_workflow_version=branch_pyproject["cubi"]["workflow"]["template"]["version"]
    target_workflow_version=target_pyproject["cubi"]["workflow"]["template"]["version"]
    # updating the workflow version in the workflow pyproject with the workflow version
    # from the template_snakemake 'source' pyproject:
    target_pyproject["cubi"]["workflow"]["template"]["version"]=branch_workflow_version

    return (
        branch_metadata_version,
        target_metadata_version,
        branch_workflow_version,
        target_workflow_version,
        target_pyproject,
    )


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

    cubi_tools_scripts = toml_file["cubi"]["tools"]["script"]
    version = None
    for cubi_tool in cubi_tools_scripts:
        if cubi_tool["name"] == __prog__:
            version = cubi_tool["version"]
    if version is None:
        raise RuntimeError(
            "Cannot identify script version from pyproject cubi-tools::scripts "
            f"entry: {cubi_tools_scripts}"
        )

    return version


if __name__ == "__main__":
    main()
