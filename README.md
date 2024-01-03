# CUBI tools

This repository is a collection of helper tools and useful scipts for interal and
external use.

## Tools

`update_workflow.py`: updates workflow files
### update_workflow.py

Whenever you want to update a snakemake workflow with the latest version of the "template-snakemake" repository you can use `update_workflow.py` to update all general files of your repository with the snakemake-template files except for the files "/workflow/rules/00_modules.smk" and "/workflow/rules/99_aggregates.smk". Those files will not be updated because they are project specific and have been modified specifically for the project. The script updates the files by identifying outdated files based on SHA checksums relative to the source repository [template-snakemake](https://github.com/core-unit-bioinformatics/template-snakemake).

# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
