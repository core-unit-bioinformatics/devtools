#!/usr/bin/env python

import os
import argparse as argp
import pathlib as pl
import multiprocessing as mp
import re
import shutil as sh
import sys
import subprocess

import yaml


__version__ = "3.0.0"


def install_snakemake_executor_plugin(args):
    """
    If using the 'Snakemake 8' option the pip plugin
    'snakemake-executor-plugin-cluster-generic' needs to be installed.
    """

    if args.infrastructure == "local":
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "snakemake-executor-plugin-cluster-generic",
            ]
        )
    else:
        smk8_env = os.environ.copy()
        smk8_env["PIP_CONFIG_FILE"] = "/software/python/pip.conf"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "snakemake-executor-plugin-cluster-generic",
        ]
        subprocess.check_call(command, env=smk8_env)
    return None


def parse_args():
    """
    Collection of the various options of the 'set_profile.py' script.
    """

    parser = argp.ArgumentParser(add_help=True)

    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s v{__version__}"
    )

    parser.add_argument(
        "--infrastructure",
        "-i",
        default="local",
        choices=["local", "hilbert"],
        dest="infrastructure",
        help="Specify execution infrastructure: local [laptop] / hilbert",
    )

    parser.add_argument(
        "--resource-preset",
        "-r",
        default=None,
        dest="preset",
        help="Specify resource preset for cluster infrastructures. "
        "This option is ignored for local execution profiles. "
        "For cluster profiles, state the path to the respective "
        "YAML file under '/resource_presets' that you want to use.",
    )

    parser.add_argument(
        "--placeholders",
        "-p",
        default=[],
        nargs="*",
        dest="placeholders",
        help="Specify placeholder replacements as space-separated list of VALUES. "
        "Currently supported for cluster infrastructure: "
        "VALUE-1 => project (qsub -A <VALUE-1> parameter) ; "
        "VALUE-2 => anchor (qsub -l anchor=<VALUE-2> parameter)",
    )

    parser.add_argument(
        "--snakemake-work-dir",
        "-w",
        type=lambda x: pl.Path(x).resolve(strict=False),
        required=True,
        dest="smk_work_dir",
        help="Path to Snakemake (pipeline) working directory. Will be created "
        "if it does not exist. Mandatory argument.",
    )

    parser.add_argument(
        "--profile-suffix",
        "-s",
        type=str,
        default="",
        dest="suffix",
        help="Append this suffix to the profile folder created in the Snakemake "
        "working directory. Examples: (no suffix) wd/prf_PROJECT ; "
        "(with suffix) wd/prf_PROJECT_suffix",
    )

    parser.add_argument(
        "--snakemake_version_8",
        "-smk8",
        action="store_true",
        default=False,
        dest="smk_version",
        help="In the new Snakemake 8 version some commands/options have been "
        "changed/deprecated. To select the modified Snakemake 8 settings activate "
        "this option by entering the argument. The default option is still "
        "using Snakemake 7",
    )

    args = parser.parse_args()

    if args.infrastructure != "local" and args.preset is None:
        raise ValueError("You need to specify a resource preset for cluster profiles!")
    return args


def pprint_cluster_config(config_string):
    """
    Convenience only - improve readability
    of cluster config string in dumped
    YAML
    """

    prettified_string = ">-\n "
    for component in config_string.split():
        if component.startswith("+"):
            prettified_string += " " + component
        elif component.startswith("-"):
            prettified_string += "\n  " + component
        else:
            prettified_string += " " + component
    return prettified_string


def replace_placeholders(placeholders, config_dump):
    """
    Function to check for and add placeholder replacements as space-separated
    list of VALUES.(VALUE-1 => project (qsub -A <VALUE-1> parameter) and
    VALUE-2 => anchor (qsub -l anchor=<VALUE-2> parameter))
    """

    for pname, pvalue in placeholders.items():
        pattern = f"<PLACEHOLDER_{pname.upper()}>"
        if re.search(pattern, config_dump) is not None:
            sys.stdout.write(f"\nReplacing placeholder {pname} with value {pvalue}\n")
            config_dump = config_dump.replace(pattern, pvalue)

    missing_placeholders = re.search("<PLACEHOLDER_\w+(>)?", config_dump)
    if missing_placeholders is not None:
        missing = missing_placeholders.group(0)
        raise ValueError(
            "Error: placeholder not replaced by value. You need "
            "to specify all concrete values via the '--placeholders' "
            f"command line option: {missing}"
        )
    assert missing_placeholders is None, missing_placeholders
    return config_dump


def load_yaml(file_path):
    """
    Load the PRESET.YAML file
    """

    with open(file_path, "rb") as yaml_file:
        content = yaml.load(yaml_file, Loader=yaml.SafeLoader)
    return content


def load_base_profile(profile_root, smk8):
    """
    Load the base_profile YAML file, depending on Snkamemake version
    """

    if not smk8:
        base_profile = profile_root.joinpath("base.yaml").resolve(strict=True)
        config = load_yaml(base_profile)
    else:
        base_profile = profile_root.joinpath("base_smk8.yaml").resolve(strict=True)
        config = load_yaml(base_profile)
    return config


def prepare_local_profile(profile_root, smk8):
    """
    Prepare the local profile config.yaml
    """

    local_cpus = mp.cpu_count()
    config = load_base_profile(profile_root, smk8)
    config["cores"] = local_cpus
    config_dump = yaml.dump(config)
    return config_dump


def prepare_cluster_profile(profile_root, smk8, rsrc_preset, placeholders):
    """
    Prepare the cluster profile config.yaml
    """

    copy_files = list(profile_root.joinpath("cluster_utils").glob("*"))
    assert len(copy_files) == 3
    # add environment config file
    # that only exists for cluster environments
    copy_files.append(profile_root.joinpath("env.yaml").resolve(strict=True))
    assert len(copy_files) == 4
    config = load_base_profile(profile_root, smk8)
    preset = load_yaml(rsrc_preset)

    for rsrc_key, rsrc_value in preset.items():
        if rsrc_key not in config:
            config[rsrc_key] = rsrc_value
        else:
            base_values = config[rsrc_key]
            if isinstance(base_values, str):
                assert isinstance(rsrc_value, str)
                updated_values = base_values + " " + rsrc_value
            elif isinstance(base_values, list):
                assert isinstance(rsrc_value, list)
                updated_values = base_values + rsrc_value
            else:
                raise ValueError(
                    f"Cannot handle resource value: {rsrc_value} / {type(rsrc_value)}"
                )
            config[rsrc_key] = updated_values
    # next: pretty print cluster config entry
    cluster_config_value = config["cluster-generic-submit-cmd"]
    config["cluster-generic-submit-cmd"] = "<CLUSTER>"
    cluster_config_value = pprint_cluster_config(cluster_config_value)
    config_dump = yaml.dump(config)
    config_dump = config_dump.replace("<CLUSTER>", cluster_config_value)

    # replace placeholders with actual user-supplied values
    config_dump = replace_placeholders(placeholders, config_dump)
    return config_dump, copy_files


def main():
    """
    Main function of the 'set_profile.py' script.
    """

    args = parse_args()
    smk8 = args.smk_version

    if smk8:
        install_snakemake_executor_plugin(args)

    profiles_dir = pl.Path(__file__).parent.joinpath("profiles").resolve(strict=True)
    profile_root = profiles_dir.joinpath(args.infrastructure).resolve(strict=True)

    known_placeholders = ["project", "anchor"]
    placeholders = dict((k, v) for k, v in zip(known_placeholders, args.placeholders))

    if args.infrastructure == "local":
        profile_cfg = prepare_local_profile(profile_root, smk8)
        copy_files = []
        placeholders = {"project": "local"}
    elif args.infrastructure in ["hilbert"]:
        profile_cfg, copy_files = prepare_cluster_profile(
            profile_root, smk8, args.preset, placeholders
        )
    else:
        raise ValueError(f"Unknown execution infrastructure: {args.infrastructure}")

    if args.suffix:
        # assert should mainly catch quirky typos
        assert args.suffix.isidentifier()
        profile_dir_name = f"prf_{placeholders['project']}_{args.suffix}"
        profile_dir = args.smk_work_dir.joinpath(profile_dir_name).resolve(strict=False)
    else:
        profile_dir_name = f"prf_{placeholders['project']}"
        profile_dir = args.smk_work_dir.joinpath(profile_dir_name).resolve(strict=False)

    profile_dir.mkdir(parents=True, exist_ok=True)
    for utils_file in copy_files:
        _ = sh.copy(utils_file, profile_dir)

    with open(profile_dir.joinpath("config.yaml"), "w", encoding="ascii") as dump:
        _ = dump.write(profile_cfg)

    return 0


if __name__ == "__main__":
    main()
