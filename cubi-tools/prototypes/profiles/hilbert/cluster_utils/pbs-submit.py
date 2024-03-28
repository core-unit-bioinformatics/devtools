#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import re

from snakemake.utils import read_job_properties


def parse_args():

    parser = argparse.ArgumentParser(prefix_chars='+', add_help=True)
    parser.add_argument(
        "++depend",
        help="Space separated list of ids for jobs this job should depend on."
    )
    parser.add_argument(
        "++no-singularity-module",
        help="Do not add the default Singularity envmodule to the jobscript, i.e. "
             "the Singularity envmodule will NOT be loaded prior to the "
             "Snakemake job execution. Default: False",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "++verbose",
        help="Print qsub command line to stderr before job submission. Default: False",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "++dry-run",
        help="Do not execute anything - use for debugging. Default: False",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "++mkdirs",
        help="Comma-separated list of directories to create to catch the stdout/stderr "
             "output files of the cluster jobs",
        default=""
    )
    parser.add_argument(
        "qsub_args",
        nargs="*",
    )
    parser.add_argument(
        "jobscript",
    )

    args = parser.parse_args()
    return args


def main():

    args = parse_args()

    if (args.verbose):
        print("pbs-submit.py received the following args:\n", args, file=sys.stderr)

    if args.no_singularity_module:
        if args.verbose:
            print("NOT adding HPC envmodule 'Singularity' to jobscript", file=sys.stderr)
        default_args = {"modules": []}
    else:
        if args.verbose:
            print("Adding HPC envmodule 'Singularity' to jobscript", file=sys.stderr)
        default_args = {"modules": ["Singularity"]}

    if args.mkdirs:
        for directory in args.mkdirs.split(","):
            os.makedirs(directory, exist_ok=True)

    try:
        job_properties = read_job_properties(args.jobscript)
    except Exception as e:
        print("FATAL ERROR: could not read job properties:", e, file=sys.stderr)
        raise

    try:
        default_args["modules"].extend(job_properties["cluster"]["modules"])
    except KeyError as ke:
        if args.verbose:
            print("WARNING: could not merge clusterArgs because of key error:", ke, file=sys.stderr)
    except Exception as e:
        print("FATAL ERROR: could not read cluster modules:", e, file=sys.stderr)
        raise

    module_string = ""
    for module in default_args["modules"]:
        module_string += "module load {}\n".format(module)

    try:
        with open(args.jobscript, "r") as f:
            jobscript_content = f.read()

        jobscript_content = re.sub('# <modules>', module_string, jobscript_content)

        if (args.verbose):
            print("Modified jobscript:\n", jobscript_content, file=sys.stderr)

        if not args.dry_run:
            with open(args.jobscript, "w") as f:
                f.write(jobscript_content)
    except Exception as e:
        print("FATAL ERROR: could not read or modify jobscript:", e, file=sys.stderr)
        raise

    depend_jobs = ""
    if args.depend:
        for m in args.depend.split(" "):
            depend_jobs = depend_jobs + ":" + m
        depend_jobs = " -W \"depend=afterok" + depend_jobs + "\""

    cmd = "qsub {} {} {}".format(depend_jobs, " ".join(args.qsub_args), args.jobscript)

    if (args.verbose):
        print(f"Submitting jobscript {args.jobscript} to the cluster with qsub command:\n{cmd}\n", file=sys.stderr)

    res = ""
    if not args.dry_run:
        try:
            res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise e
        res = res.stdout.decode().strip()
        print(res, file=sys.stdout)

    return 0


if __name__ == '__main__':
    main()
