#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import os
import shutil
import hashlib
import toml

# sys.tracebacklimit = -1


def main():
    """
    Main function of the 'update-workflow.py' script.
    """

    args = parse_command_line()
    dryrun = args.dryrun

    # Is it a dry run?
    if dryrun:
        print("\nTHIS IS A DRY RUN!!")

    # report version of script
    if args.version:
        print(f"\nScript version: {report_script_version()}\n")

    # check if project directory exist:
    project_dir = pathlib.Path(args.project_dir).resolve()
    assert project_dir.is_dir(), f"The project directory {project_dir} doesn't exist!"
    print(f"Project directory set as: {project_dir}\n")

    ref_repo = args.ref_repo
    source = args.source
    metadata = args.metadata

    # Since using the online github repo directly to update the local workflow files
    # is resulting in hitting an API rate limit fairly quickly a local copy is needed.
    # The location of the template_snakemake folder holding branch/version tag
    # of interest is on the same level as the project directory
    template_dir = pathlib.Path(
        pathlib.Path(f"{project_dir}").resolve().parents[0],
        "template-snakemake",
    ).resolve()

    # detect if workflow is based on CUBI's template_snakemake repo
    # The file '/workflow/rules/commons/10_constants.smk' should be present
    # if template_snakemake was used to create project folder
    if pathlib.Path(
        str(project_dir) + "/workflow/rules/commons/10_constants.smk"
    ).is_file():
        pass
    else:
        question = user_response(
            "ARE YOU SURE THIS PROJECT IS BASED ON CUBI'S "
            "'template_snakemake' REPOSITORY"
        )
        if question:
            pass
        else:
            raise NameError(
                "This project is not based on CUBI's 'template_snakemake'. "
                "No changes have been made!"
            )

    # Clone/update the 'template-snakemake' repo
    # into a local folder if it exists
    clone(project_dir, ref_repo, source, template_dir, dryrun)

    # Call function to create the list of files and folders that
    # should be made/copied/updated
    files_to_update = update_file_list(template_dir, metadata, dryrun)[0]

    dirs_in_template = update_file_list(template_dir, metadata, dryrun)[1]
    dirs_to_make = [
        path.replace(str(template_dir), str(project_dir)) for path in dirs_in_template
    ]
    for items in dirs_to_make:
        os.makedirs(items, exist_ok=True)

    # Updating routine of the metadata files
    for f in files_to_update:
        if f == "pyproject.toml":
            update_pyproject_toml(project_dir, template_dir, source, dryrun)
        else:
            print(
                f"Comparing if local '{f}' differs from version in branch/version tag "
                f"'{source}' in the 'template-snakemake' repo"
            )
            update_file(f, project_dir, template_dir, dryrun)

    # For 'git pull' you have to be in a branch of the template-snakemake repo to
    # merge with. If you previously chose a version tag to update from, 'git pull' will
    # throw a waning message. This part will reset the repo to the main branch to avoid
    # any warning message stemming from 'git pull'
    command_reset = ["git", "checkout", "main", "-q"]
    sp.run(
        command_reset,
        cwd=template_dir,
        check=False,
    )

    print("\nUPDATE COMPLETED!")

    return None


def parse_command_line():
    """
    Collection of the various options of the 'update-workflow.py' script.
    """
    parser = argp.ArgumentParser(
        description="Add or update workflow files for your repository. "
        "Example: python3 update_workflow.py --project-dir path/to/repo"
    )
    parser.add_argument(
        "--project-dir",
        "-p",
        type=pathlib.Path,
        help="(Mandatory) Directory where workflow template files "
        "should be copied/updated.",
        required=True,
    )
    parser.add_argument(
        "--ref-repo",
        type=str,
        nargs="?",
        default="https://github.com/core-unit-bioinformatics/template-snakemake.git",
        help="Reference/remote repository used to clone files.",
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
        "--metadata",
        "-m",
        action="store_true",
        default=False,
        dest="metadata",
        help="If False (default), the metadata files will not be updated",
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


def clone(project_dir, ref_repo, source, template_dir, dryrun):
    """
    Check if the 'template-snakemake' repo is already parallel to the
    project directory. If the 'template-snakemake' repo exists this folder is
    getting updated via a 'git pull --all' command. If that is not the case,
    the 'template-snakemake' repo will be cloned parallel to the project
    directory unless the branch or version tag don't exist,
    then an AssertionError will be called to stop the script.
    """
    if dryrun:
        if not template_dir.is_dir():
            raise NameError(
                "The 'template-snakemake' repo needs to be present in the "
                f"parental folder of the project directory {project_dir}.\n"
                "In a live run the 'template-snakemake' repo would "
                f"be created at {template_dir}.\n"
            )
        else:
            print(
                "The folder 'template-snakemake' is present "
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
                cwd=template_dir,
                check=False,
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            checkout_cmd = sp.run(
                command_checkout,
                cwd=template_dir,
                stderr=sp.PIPE,
                check=False,
            )
            # If the 'template-snakemake' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(checkout_cmd.stderr.strip()), (
                "The folder 'template-snakemake' is not a git repository! "
                "For this script to work either delete the folder or move it!!"
            )
            # If you try to clone a repo/branch/tag that doesn't exist
            # Git will throw an error message that contains the string 'error:'
            error = "error:"
            assert error not in str(
                checkout_cmd.stderr.strip()
            ), f"The branch or version tag named '{source}' doesn't exist"
    else:
        if template_dir.is_dir():
            command = [
                "git",
                "pull",
                "--all",
                "-q",
            ]
            sp.run(
                command,
                cwd=template_dir,
                check=False,
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            checkout_cmd = sp.run(
                command_checkout,
                cwd=template_dir,
                stderr=sp.PIPE,
                check=False,
            )
            # If the 'template-snakemake' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(checkout_cmd.stderr.strip()), (
                "The folder 'template-snakemake' is not a git repository! "
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
                template_dir,
            ]
            clone_cmd = sp.run(
                command,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                cwd=project_dir,
                check=False,
            )
            # If the 'template-snakemake' folder is not a Git repo
            # an error message that contains the string 'fatal:' will be thrown
            warning = "fatal:"
            assert warning not in str(clone_cmd.stderr.strip()), (
                "The repository you entered or the branch or version tag "
                f"named '{source}' doesn't exist"
            )
            command_checkout = ["git", "checkout", "".join({source}), "-q"]
            sp.run(
                command_checkout,
                cwd=project_dir,
                check=False,
            )
    return None


def get_local_checksum(project_dir, f):
    """
    The MD5 checksum for all workflow files in the
    local project directory is determined.
    """
    if project_dir.joinpath(f).is_file():
        with open(project_dir.joinpath(f), "rb") as local_file:
            # read contents of the file
            local_data = local_file.read()
            # pipe contents of the file through
            md5_local = hashlib.md5(local_data).hexdigest()
    else:
        md5_local = ""
    return md5_local


def get_ref_checksum(template_dir, f):
    """
    The MD5 checksum for all workflow files in the temp folder
    for the desired branch or version tag is determined.
    """
    with open(template_dir.joinpath(f), "rb") as ref_file:
        # read contents of the file
        ref_data = ref_file.read()
        # pipe contents of the file through
        md5_ref = hashlib.md5(ref_data).hexdigest()
    return md5_ref


def update_file(f, project_dir, template_dir, dryrun):
    """
    The MD5 checksum of the the local workflow file(s) and the workflow
    file(s) in the desired branch or version tag are being compared.
    If they differ a question to update for each different
    workflow file pops up. If an update is requested it will be performed.
    """
    if dryrun:
        local_sum = get_local_checksum(project_dir, f)
        ref_sum = get_ref_checksum(template_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            print(f"Update '{f}'(y/n)? y")
            print(f"Dry run! '{f}' would be updated!")
        else:
            print(f"Dry run! '{f}' is up-to-date!")
    else:
        local_sum = get_local_checksum(project_dir, f)
        ref_sum = get_ref_checksum(template_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            question = user_response(f"Update '{f}'")

            if question:
                shutil.copyfile(template_dir.joinpath(f), project_dir.joinpath(f))
                print(f"'{f}' was updated!")
            else:
                print(f"'{f}' was NOT updated!")
        else:
            print(f"'{f}' is up-to-date!")
        return None


def update_pyproject_toml(project_dir, template_dir, source, dryrun):
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
    if dryrun:
        if not project_dir.joinpath("pyproject.toml").is_file():
            print(
                "\nThere is no 'pyproject.toml' in your folder. "
                "Do you want to add 'pyproject.toml'(y/n)? y"
                "\nDry run! 'pyproject.toml' would have been added!"
            )
        else:
            comparison = compare_pyproject_versions(project_dir, template_dir)
            # Just to clearly state which information/files are generated by the
            # function 'compare_pyproject_versions(project_dir, template_dir)':
            template_metadata_version = comparison[0]
            project_metadata_version = comparison[1]
            template_workflow_version = comparison[2]
            project_workflow_version = comparison[3]

            if (
                template_metadata_version != project_metadata_version
                or template_workflow_version != project_workflow_version
            ):
                print(
                    "\nYou updated your local repo with the 'template_snakemake' "
                    f"branch/version tag '{source}'."
                    "\nDo you want to update the the metadata and workflow versions "
                    "in 'pyproject.toml'(y/n)? y"
                )
                print(
                    "Dry run!\n"
                    "\nMetadata version in 'pyproject.toml' would have been updated "
                    f"from version '{project_metadata_version}' to version "
                    f"'{template_metadata_version}'! and "
                    "\nWorkflow version in 'pyproject.toml' would have been updated "
                    f"from version '{project_workflow_version}' to version "
                    f"'{template_workflow_version}'!"
                )
            else:
                print(
                    "\nDry run! Metadata and workflow versions in 'pyproject.toml' "
                    "are up-to-date!\n"
                )
    else:
        if not project_dir.joinpath("pyproject.toml").is_file():
            question = user_response(
                "There is no 'pyproject.toml' in your folder. Add 'pyproject.toml'"
            )

            if question:
                shutil.copyfile(
                    template_dir.joinpath("pyproject.toml"),
                    project_dir.joinpath("pyproject.toml"),
                )
                print("'pyproject.toml' was added!")
            else:
                print("'pyproject.toml' was NOT added!")

        else:
            comparison = compare_pyproject_versions(project_dir, template_dir)
            # Just to clearly state which information/files are generated by the
            # function 'compare_pyproject_versions(project_dir, template_dir)':
            template_metadata_version = comparison[0]
            project_metadata_version = comparison[1]
            template_workflow_version = comparison[2]
            project_workflow_version = comparison[3]
            new_project_pyproject = comparison[4]

            if (
                template_metadata_version != project_metadata_version
                or template_workflow_version != project_workflow_version
            ):
                question = user_response(
                    "\nYou updated your local repo with the 'template_snakemake' "
                    f"branch/version tag '{source}'."
                    "\nDo you want to update the metadata and workflow versions in "
                    "'pyproject.toml'"
                )

                if question:
                    with open(
                        pathlib.Path(project_dir, "pyproject.toml"),
                        "w",
                        encoding="utf-8",
                    ) as text_file:
                        text_file.write(toml.dumps(new_project_pyproject, encoder=None))
                    print(
                        "\nMetadata version in 'pyproject.toml' was updated from "
                        f"version '{project_metadata_version}' to version "
                        f"'{template_metadata_version}'! and "
                        "\nWorkflow version in 'pyproject.toml' was updated from "
                        f"version '{project_workflow_version}' to version "
                        f"'{template_workflow_version}'!"
                    )
                else:
                    print(
                        "The 'pyproject.toml' metadata version was NOT updated from "
                        f"version '{project_metadata_version}' to version "
                        f"'{template_metadata_version}' and "
                        "The 'pyproject.toml' workflow version was NOT updated from "
                        f"version '{project_workflow_version}' to version "
                        f"'{template_workflow_version}'!"
                    )
            else:
                print(
                    "\nMetadata and workflow versions in 'pyproject.toml' are "
                    "up-to-date!\n"
                )
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


def fast_scandir(template_dir):
    """
    Function to list all subdirectories in the 'template_snakemake' repo
    to be able to create all missing subfolders.
    """
    subfolders = [f.path for f in os.scandir(template_dir) if f.is_dir()]
    for template_dir in list(subfolders):
        subfolders.extend(fast_scandir(template_dir))
    return subfolders


def update_file_list(template_dir, metadata, dryrun):
    """
    Function to create a list of files that will be updated.
    """
    files_to_update = []
    # create a list of all files in 'template_snakemake' directory
    workflow_files = []
    for file in template_dir.rglob("*"):
        if file.is_file():
            workflow_files.append(str(pathlib.Path(file).relative_to(template_dir)))

    # the following files need to be excluded because they are always project specific
    excluded_files = [
        "pyproject.toml",
        "workflow/rules/00_modules.smk",
        "workflow/rules/99_aggregate.smk",
    ]
    workflow_files = [item for item in workflow_files if item not in excluded_files]
    # the '.git' folder also needs to be excluded from the update list!
    workflow_files = [item for item in workflow_files if ".git/" not in item]
    # I want the 'pyproject.toml' file at the end of the list and therefore I excluded
    # it initially from the list and now I append it so it will be at the end
    workflow_files.append("pyproject.toml")

    subfolders = [f.path for f in os.scandir(template_dir) if f.is_dir()]
    for template_dir in list(subfolders):
        subfolders.extend(fast_scandir(template_dir))
    subfolders = [item for item in subfolders if ".git" not in item]

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


def compare_pyproject_versions(project_dir, template_dir):
    """
    Function to compare the metadata and workflow version number in the
    pyproject.toml of the local repository with the metadata version and
    the workflow version of the pyproject.toml of the source 'template_snakemake'.
    """
    # loading the pyproject.tomls:
    template_pyproject = toml.load(
        pathlib.Path(template_dir, "pyproject.toml"), _dict=dict
    )
    project_pyproject = toml.load(
        pathlib.Path(project_dir, "pyproject.toml"), _dict=dict
    )
    # extracting the metadata versions:
    template_metadata_version = template_pyproject["cubi"]["metadata"]["version"]
    project_metadata_version = project_pyproject["cubi"]["metadata"]["version"]
    # updating the metadata version in the workflow pyproject with the metadata version
    # from the template_snakemake 'source' pyproject:
    project_pyproject["cubi"]["metadata"]["version"] = template_metadata_version

    # extracting the workflow versions:
    template_workflow_version = template_pyproject["cubi"]["workflow"]["template"][
        "version"
    ]
    project_workflow_version = project_pyproject["cubi"]["workflow"]["template"][
        "version"
    ]
    # updating the workflow version in the workflow pyproject with the workflow version
    # from the template_snakemake 'source' pyproject:
    project_pyproject["cubi"]["workflow"]["template"][
        "version"
    ] = template_workflow_version

    return (
        template_metadata_version,
        project_metadata_version,
        template_workflow_version,
        project_workflow_version,
        project_pyproject,
    )


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
