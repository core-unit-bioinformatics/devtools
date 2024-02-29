# Snakemake Utilities / CUBI

This repository contains a script to generate Snakemake profiles from a generic config and resource presets. Currently, the data in this repository support generating Snakemake profiles for the HHU cluster "HILBERT", and for local execution such as on a laptop.

## Usage

If necessary, create the Conda environment specified in `envs/smk_profile.yaml` to have the pyYAML package available.

Run the script `set_profile.py --help` to display the command line help.

Briefly, the mode of operation is as follows:

1. specify the infrastructrue (`-i`) you are targeting: `local` or `hilbert`
2. if you plan on using Snakemake version 8.x you have to enter `-smk8` because starting with Snakemake 8.0 some options/commands have been deprecated or renamed
3. for cluster execution, select a resource preset YAML file (`-r`) located in `profiles/<CLUSTER>/resource_presets/<PRESET>.yaml`
    - the preset equivalent to the Snakemake profile up to release/tag v1.0.0 of this repository is `mem-mb_walltime_wo-bonus.yaml`
    - if you activated `-smk8` make sure that you select a Snakemake 8.x adjusted YAML file located in `profiles/<CLUSTER>/resource_presets/<PRESET>_smk8.yaml`
4. specify the values to replace the placeholders as an ordered list (`-p`). The current set of recognized placeholders are - in that order - the "project" name and the "anchor" name (context: bonus/priority points).
5. specify the Snakemake working directory via `-w`, the profile will be copied to this folder. This file copying is done because Snakemake does not reasonably resolve paths to the files mentioned in the profile.
    - if you generate several profiles, e.g., one with and one with using bonus points, you can also specify a suffix via `-s` that will be appended to the profile folder name.

Having generated your execution profile, you can run `snakemake` as follows:

```bash
$ snakemake -d SNAKEMAKE-WORK-DIR/ --profile SNAKEMAKE-WORK-DIR/prf_<PROJECT>_<SUFFIX> [...]
```

As explained above, the `SUFFIX` part is optional.

If you execute your workflow on an HPC cluster, the created profile folder includes a special config file `env.yaml`
that contains information on available CPU cores and common (and maximal) memory configurations of the
cluster compute nodes (= the job execution servers). Using that information requires loading this configuration
file via the `--configfiles` parameters:

```bash
$ snakemake -d SNAKEMAKE-WORK-DIR/ \
    --profile SNAKEMAKE-WORK-DIR/prf_<PROJECT>_<SUFFIX> \
    --configfiles SNAKEMAKE-WORK-DIR/prf_<PROJECT>_<SUFFIX>/env.yaml \
    [...]
```

Note that the CUBI Snakemake workflow template sets (low) default values for the available CPU cores, so it is
strongly recommended to make use of the `env.yaml` configuration file.

### Cluster logs

Note that the `pbs-submit.py` script includes the option to create the required directories that are the destinations for `stdout` and `stderr` of the cluster jobs:

```
pbs-submit.py ++mkdirs clusterLogs/err,clusterLogs/out [...]
```

These directory names match what is then specified further down in the profile:

```
  -e clusterLogs/err/{rule}.{jobid}.stderr
  -o clusterLogs/out/{rule}.{jobid}.stdout
```

If these folders do not exist at runtime, you'll receive PBS error notifications via e-mail.

## Contributors

- HHU/CUBI source
    - Developer: Peter Ebert
- HHU source
    - Developer: Lukas Rose
- Original source
    - Copyright: 2017 Snakemake-Profiles
    - License: MIT
    - Developer: gh#neilav
    - URL: https://github.com/Snakemake-Profiles/pbs-torque
