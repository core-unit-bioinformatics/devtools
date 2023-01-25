import os
from pathlib import Path
import subprocess as sp
import argparse as argp


def main():
    args=parse_command_line()
    project_dir = args.project_dir
    print(f"Project directory set as: {project_dir}")
    ref_repo_clone = args.ref_repo_clone

    # get metafiles if none are present
    if not any(project_dir.iterdir()):
        clone(project_dir, ref_repo_clone)
    # else update files
    else:
        files_to_update = ["CITATION.md"]
        [update_file(f, project_dir) for f in files_to_update]

def parse_command_line():
    parser = argp.ArgumentParser()
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Directory where metafiles should be copied/updated.",
    )
    parser.add_argument(
        "ref_repo_clone",
        type=str,
        nargs="?",
        default="git@github.com:core-unit-bioinformatics/template-metadata-files.git",
        help="Reference/remote repository used to clone files.",
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


def update_file(f, project_dir):
    command = ["git", "hash-object", os.path.join(project_dir, f)]
    sha1Sum = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=project_dir,
    )
    sha1Sum = sha1Sum.stdout.strip()
    command = [
        "curl",
        "https://api.github.com/repos/core-unit-bioinformatics/template-metadata-files/contents/"
        + f,
    ]
    sha1SumRef = sp.run(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        cwd=project_dir,
    )
    sha1SumRef = sha1SumRef.stdout.split('"')[11]
    if not sha1Sum == sha1SumRef:
        print(f"File: {f} differs.")
        print(f"Local SHA checksum: {sha1Sum}")
        print(f"Remote SHA checksum: {sha1SumRef}")
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
                "https://raw.githubusercontent.com/core-unit-bioinformatics/template-metadata-files/main/"
                + f,
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
