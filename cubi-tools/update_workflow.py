#!/usr/bin/env python3

import pathlib
import sys
import subprocess as sp
import argparse as argp
import hashlib
import shutil
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
        print(f"\nScript version: {report_script_version()}")

    project_dir = pathlib.Path(args.project_dir).resolve()
    print(f"\nProject directory set as: {project_dir}\n")
    ref_repo = args.ref_repo
    source = args.source
    keep = args.keep
    metadata = args.metadata

    # Since using the online github repo directly to update the local workflow files
    # is resulting in hitting an API rate limit fairly quickly a local copy is needed.
    # The location of the template_snakemake folder holding branch/version tag of interest
    # is on the same level as the project directory
    template_dir = pathlib.Path(
        pathlib.Path(f"{project_dir}").resolve().parents[0],
        f"template_snakemake/{source}",
    ).resolve()

    # detect if workflow is based on CUBI's template_snakemake repo
    # The file '/workflow/rules/commons/10_constants.smk' should be present if template_snakemake was used to create project folder
    if pathlib.Path(
        str(project_dir) + "/workflow/rules/commons/10_constants.smk"
    ).is_file():
        pass
    else:
        question = user_response(
            "ARE YOU SURE THIS PROJECT IS BASED ON CUBI'S 'template_snakemake'"
        )
        if question:
            pass
        else:
            raise Exception(
                "This project is not based on CUBI's 'template_snakemake'. No changes have been made!"
            )

    # Clone the 'template-snakemake' branch or version tag into a local folder if it exists
    try:
        clone(project_dir, ref_repo, source, template_dir, dryrun)
    except AssertionError:
        raise AssertionError(
            f"The repository you entered or the branch or version tag named '{source}' doesn't exist"
        ) from None

    # Call function to create the list of files that should be copied/updated
    files_to_update = update_file_list(template_dir, metadata, dryrun)

    # Updating routine of the metadata files
    for f in files_to_update:
        if f == "pyproject.toml":
            update_pyproject_toml(project_dir, template_dir, source, dryrun, metadata)
        else:
            print(
                f"Comparing if local '{f}' differs from version in branch/version tag "
                f"'{source}' in the 'template-metadata-files' repo"
            )
            update_file(f, project_dir, template_dir, dryrun)

    # detect if metafiles temp folder should be kept
    if keep:
        print(
            f"\nYou want to keep the files of the branch/version tag '{source}' of the 'template-snakemake' folder.\n"
            f"It's located at '{template_dir}'"
        )
    else:
        rm_temp(template_dir.parent, dryrun)
        # print("\nThe 'template_metadata_files' folder with all files and subfolders has been deleted!")

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
        type=pathlib.Path,
        help="(Mandatory) Directory where workflow template files should be copied/updated.",
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
        "--keep",
        "-k",
        action="store_true",
        default=False,
        dest="keep",
        help="If False (default), the workflow template files source repo will be deleted when script finishes"
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
    Check if the branch or version tag that contains the desired workflow template files
    is already in a temp folder within the project directory.
    If that is not the case, the desired branch or version tag will be cloned into
    a temp folder parallel to the project directory unless the branch or version tag don't exist,
    then an AssertionError will be called to stop the script.
    If a temp folder for the branch or version tag exists this folder is getting updated via
    a git pull command.
    """
    if dryrun:
        if not template_dir.is_dir():
            print(
                f"\nThe requested branch/version tag (default: main) is being copied to {template_dir}."
            )
        else:
            print(
                "\nThe requested branch/version tag (default: main) already exists and is getting updated."
            )
    else:
        if not template_dir.is_dir():
            command = [
                "git",
                "clone",
                "-q",
                "-c advice.detachedHead=false",
                "--depth=1",  # depth =1 to avoid big .git file
                "--branch",
                source,
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
                cwd=template_dir,
                check=False,
            )
    return None


def get_local_checksum(project_dir, f):
    """
    The MD5 checksum for all workflow files in the local project directory is determined.
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
    The MD5 checksum for all workflow files in the temp folder for the desired branch or version tag is determined.
    """
    with open(template_dir.joinpath(f), "rb") as ref_file:
        # read contents of the file
        ref_data = ref_file.read()
        # pipe contents of the file through
        md5_ref = hashlib.md5(ref_data).hexdigest()
    return md5_ref


def update_file(f, project_dir, template_dir, dryrun):
    """
    The MD5 checksum of the the local workflow file(s) and the workflow file(s) in the desired
    branch or version tag are being compared. If they differ a question to update for each different
    workflow file pops up. If an update is requested it will be performed.
    """
    if dryrun:
        print(f"Dry run! {f} updated!")
    else:
        local_sum = get_local_checksum(project_dir, f)
        ref_sum = get_ref_checksum(template_dir, f)
        if local_sum != ref_sum:
            print(f"The versions of '{f}' differ!")
            print(f"Local MD5 checksum: {local_sum}")
            print(f"Remote MD5 checksum: {ref_sum}")
            question = user_response(f"Update '{f}'")

            if question:
                command = [
                    "cp",
                    template_dir.joinpath(f),
                    project_dir.joinpath(f),
                ]
                sp.run(command, cwd=project_dir, check=False)
                print(f"'{f}' was updated!")
            else:
                print(f"'{f}' was NOT updated!")
        else:
            print(f"'{f}' is up-to-date!")
        return None


def update_pyproject_toml(project_dir, template_dir, source, dryrun, metadata):
    """
    The 'pyproject.toml' is treated a little bit differently. First, there is a check if
    the file even exists in the project directory. If that is not the case it will be copied
    into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.workflow.template.version (and only that information!)
    differs between the local and the requested branch or version tag version. If that is the case the
    cubi.workflow.template.version is getting updated.
    If the 'metadata' switch is set also the cubi.metadata.version will be updated (if necessary).
    """
    x = "pyproject.toml"
    if dryrun:
        print(f"Dry run! '{x}' added or updated!")
    else:
        if metadata:
            update_pyproject_toml_workflow(project_dir, template_dir, source)
            update_pyproject_toml_metadata(project_dir, template_dir, source)
        else:
            update_pyproject_toml_workflow(project_dir, template_dir, source)
    return None


def rm_temp(pth: pathlib.Path, dryrun):
    """
    Remove all files and folders from template_snakemake folder
    that contains the downloaded workflow files
    """
    if dryrun:
        pass
    else:
        shutil.rmtree(pth)
    return None


def user_response(question):
    """
    Function to evaluate the user response to the Yes or No question refarding updating
    the workflow files.
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

    # the following files need to be excluded because they are allways project specific
    exclude_files = ["workflow/rules/00_modules.smk", "workflow/rules/99_aggregate.smk"]
    workflow_files = [item for item in workflow_files if item not in exclude_files]
    # the '.git' folder also needs to be excluded from the update list!
    workflow_files = [item for item in workflow_files if ".git/" not in item]

    # metadata files
    metadata_files = [
        "CITATION.md",
        "LICENSE",
        ".editorconfig",
    ]
    if dryrun:
        if metadata:
            files_to_update = [
                "CITATION.md",
                "workflow/rules/commons/00_commons.smk",
                "pyproject.toml",
            ]
            print(
                "\nAll workflow files including metadata files will be copied/updated!\n"
            )
        else:
            files_to_update = [
                "README.md",
                "workflow/rules/commons/00_commons.smk",
                "pyproject.toml",
            ]
            print(
                "\nJust the workflow files without the metadata files will be copied/updated!\n"
            )
    else:
        if metadata:
            files_to_update = workflow_files
        else:
            files_to_update = [
                item for item in workflow_files if item not in metadata_files
            ]
    return files_to_update


def update_pyproject_toml_workflow(project_dir, template_dir, source):
    """
    First, there is a check if 'pyproject.toml' even exists in the project directory.
    If that is not the case it will be copied into that folder from the desired branch or version tag.
    If the file is present it will be checked if the cubi.workflow.template.version (and only that information!)
    differs between the local and the requested branch or version tag version. If that is the case the
    cubi.workflow.template.version is getting updated.
    """
    x = "pyproject.toml"
    if not project_dir.joinpath(x).is_file():
        question = user_response(
            f"There is no 'pyproject.toml' in your folder. Add '{x}'"
        )
        if question:
            command = [
                "cp",
                template_dir.joinpath(x),
                project_dir.joinpath(x),
            ]
            sp.run(command, cwd=project_dir, check=False)
            print(f"'{x}' was added!")
        else:
            print(f"'{x}' was NOT added!")
    else:
        command = [
            "cp",
            template_dir.joinpath(x),
            pathlib.Path(project_dir, x + ".temp"),
        ]
        sp.run(command, cwd=project_dir, check=False)
        version_new = toml.load(pathlib.Path(project_dir, x + ".temp"), _dict=dict)
        version_old = toml.load(pathlib.Path(project_dir, x), _dict=dict)
        version_new = version_new["cubi"]["workflow"]["template"]["version"]
        version_old_print = version_old["cubi"]["workflow"]["template"]["version"]
        version_old["cubi"]["workflow"]["template"]["version"] = version_new

        if version_old_print != version_new:
            question = user_response(
                f"\nYou updated your local repo with the 'template-snakmake' in branch/version tag '{source}'."
                f"\nDo you want to update the workflow template version in '{x}'"
            )
            if question:
                toml.dumps(version_old, encoder=None)
                with open(
                    pathlib.Path(project_dir, x), "w", encoding="utf-8"
                ) as text_file:
                    text_file.write(toml.dumps(version_old, encoder=None))
                pathlib.Path(project_dir, x + ".temp").unlink()
                print(
                    f"Workflow template version in '{x}' was updated from version "
                    f"'{version_old_print}' to version '{version_new}'!\n"
                )
            else:
                pathlib.Path(project_dir, x + ".temp").unlink()
                print(
                    f"'{x}' was NOT updated from version '{version_old_print}' to version '{version_new}'!"
                )
        else:
            pathlib.Path(project_dir, x + ".temp").unlink()
            print(f"\nWorkflow template version in '{x}' is up-to-date!\n")
    return None


def update_pyproject_toml_metadata(project_dir, template_dir, source):
    """
    The test if 'pyproject.toml' is present will be checked in the function 'update_pyproject_toml_workflow'
    then it will be tested if the cubi.metadata.version (and only that information!)
    differs between the local and the requested branch or version tag version. If that is the case the
    cubi.metadata.version is getting updated.
    """
    x = "pyproject.toml"
    command = [
        "cp",
        template_dir.joinpath(x),
        pathlib.Path(project_dir, x + ".temp"),
    ]
    sp.run(command, cwd=project_dir, check=False)
    version_new = toml.load(pathlib.Path(project_dir, x + ".temp"), _dict=dict)
    version_old = toml.load(pathlib.Path(project_dir, x), _dict=dict)
    version_new = version_new["cubi"]["metadata"]["version"]
    version_old_print = version_old["cubi"]["metadata"]["version"]
    version_old["cubi"]["metadata"]["version"] = version_new

    if version_old_print != version_new:
        question = user_response(
            f"\nYou updated your local repo with the 'template-metadata-files' in branch/version tag '{source}'."
            f"\nDo you want to update the metadata files version in '{x}'"
        )
        if question:
            toml.dumps(version_old, encoder=None)
            with open(pathlib.Path(project_dir, x), "w", encoding="utf-8") as text_file:
                text_file.write(toml.dumps(version_old, encoder=None))
            pathlib.Path(project_dir, x + ".temp").unlink()
            print(
                f"Metadata version in '{x}' was updated from version "
                f"'{version_old_print}' to version '{version_new}'!\n"
            )
        else:
            pathlib.Path(project_dir, x + ".temp").unlink()
            print(
                f"'{x}' was NOT updated from version '{version_old_print}' to version '{version_new}'!\n"
            )
    else:
        pathlib.Path(project_dir, x + ".temp").unlink()
        print(f"\nMetadata version in '{x}' is up-to-date!\n")
    return None


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
