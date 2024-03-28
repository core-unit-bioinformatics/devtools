#!/bin/sh
# properties = {properties}

# If really needed for debugging, uncomment the following two lines:
#echo "Will execute the following jobscript: "
#cat $0

# Will be inserted by pbs-submit.py
# <modules>

# 2022-03-31
# Properly set TMPDIR and change the default location
# of SINGULARITY_CACHEDIR to the (node-local) temp storage.
# At the time writing, this deals with certain Singularity
# problems when too many container run in parallel and dump
# their rootfs all to the same location on the /gpfs
# (default: /gpfs/scratch/$USER/.singularity)
# CAVEAT: the node-local temp storage is not monitored and
# cannot be requested as a job resources, which increases
# the risk of job failures because the node is running out
# of temp storage.

# As long as the node-local temp storage is not monitored
# by PBS, track the info in the job output logs for
# potential debugging purposes.

echo "Execution host:"
echo `uname -a`
echo "Size of /tmp:"
echo `df -h /tmp`

# Unlikely: if a jobscript is not executed via
# the cluster scheduler (PBS), it will nevertheless
# create a temp directory, which needs to be
# cleaned up after the job (no matter the job's exit status)
TMPCLEANUP="MANUAL"

if [[ -d $TMPDIR ]];
then
    echo "TMPDIR is set to: $TMPDIR"
    TMPCLEANUP="AUTO"
else
    echo "No TMPDIR set"
    TMPDIR=$(mktemp -d -t $USER-task-XXXXXXXX)
    echo "TMPDIR set to: $TMPDIR"
fi;

# set all of these in case some tool dev doesn't know
# how to properly request a temp file...
TEMP=$TMPDIR
TEMPDIR=$TMPDIR
TMP=$TMPDIR
echo "Set env vars TEMP / TEMPDIR / TMP to $TMPDIR"
SINGULARITY_CACHEDIR=$TMPDIR/.singularity/cache
SINGULARITY_TMPDIR=$TMPDIR/.singularity/tmpdir
echo "SINGULARITY_CACHEDIR set to $SINGULARITY_CACHEDIR"
echo "SINGULARITY_TMPDIR set to $SINGULARITY_TMPDIR"

{exec_job}

# 2022-04-07 note: for Snakemake cluster jobs, this last
# part of the jobscript is not triggered if a cluster
# status command script is configured at the Snakemake
# command line (or profile). If so, the Snakemake
# command is extended with " && exit 0 || exit 1"
# (see "executors.py"), presumably to ensure always
# returning 0 or 1. In a cluster run, this seems
# acceptable since the scheduler will take care of
# cleaning up $TMPDIR.

# Capture job's exit status before triggering 
# potential cleanup operations

JOBEXIT=$?

if [[ "$TMPCLEANUP" = "MANUAL" ]];
then
    echo "Deleting TMPDIR: $TMPDIR"
    rm -rfd $TMPDIR
fi;

echo "Done - job exit status: $JOBEXIT"
exit $JOBEXIT
