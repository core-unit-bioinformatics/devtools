# CUBI tools

This repository is a collection of helper tools and useful scipts for interal and
external use.

## Tools

- `update_metadata.py`: updates metadata files or initialized a new repo with metadata files
- `update_workflow.py`: updates templated workflow files

### update_metadata.py

Whenever you create a new repository you can use `update_metadata.py` to either populate your repository with
metadata files from scratch or update current metadata files. The script does so by identifying outdated files based on SHA checksums relative to the source repository [template-metadata-files](https://github.com/core-unit-bioinformatics/template-metadata-files).


### update_workflow.py

Whenever you want to update a Snakemake workflow with the latest version of the "template-snakemake" repository, you can use `update_workflow.py`.
The script updates all Snakemake template workflow files except for `/workflow/rules/00_modules.smk` and `/workflow/rules/99_aggregate.smk`,
which are assumed to contain workflow-specific modifications, i.e. module includes and result file aggregations. The script updates the template
workflow files by checking for SHA checksum differences relative to the source repository [template-snakemake](https://github.com/core-unit-bioinformatics/template-snakemake).

# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
