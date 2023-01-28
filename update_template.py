import os
import pathlib
import subprocess as sp
import argparse as argp


def main():
    args = parse_command_line()
    project_dir = args.project_dir
    print(f"Project directory set as: {project_dir}")
    ref_repo_clone = args.ref_repo_clone
    ref_repo_curl = args.ref_repo_curl
    ref_repo_wget = args.ref_repo_wget

    # get metafiles if none are present
    if not any(project_dir.iterdir()):
        clone(project_dir, ref_repo_clone)
    # else update files
    else:
        files_to_update = ["CITATION.md"]
        [
            update_file(f, project_dir, ref_repo_curl, ref_repo_wget)
            for f in files_to_update
        ]


def parse_command_line():
    parser = argp.ArgumentParser()
    parser.add_argument(
        "--project-dir",
        type=pathlib.Path,
        help="Directory where metafiles should be copied/updated.",
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
    args = parser.parse_args()
    return args


def clone(project_dir, ref_repo_clone):  # copy all metafiles
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


# remove .git .gitignore


def get_local_checksum(project_dir, f):
    command = ["git", "hash-object", project_dir.joinpath(f)]
    sha1Sum = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=project_dir,
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


def update_file(f, project_dir, ref_repo_curl, ref_repo_wget):
    local_sum = get_local_checksum(project_dir, f)
    ref_sum = get_ref_checksum(ref_repo_curl, f, project_dir)
    if not local_sum == ref_sum:
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
            sp.call(command, cwd=project_dir)
            print("Updated!")
        else:
            print("Nothing to update.")
    else:
        print("Nothing to update.")


if __name__ == "__main__":
    main()
