# Template Metadata files

This repository is a collection of metadata files that should be used to initialize new repositories
if appropriate (no strong arguments speak against it).

## Repository-related metadata files

- `LICENSE`: using this file is mandatory for all CUBI repositories
- `CITATION.md`: using this file is mandatory for all CUBI repositories
  - if no other - more specific - citation information applies to a repository,
    a link to this CITATION file must be added at the end of the top-level
    repository README (same wording as at the end of this README).
- `.editorconfig`: using this file is mandatory for all CUBI repositories
- `.gitignore`: strongly recommended, contains ignore rules for Python, R and some custom entries by default.
    There must be a good reason not to use (an extended version of) this file.

## CUBI metdata files

By convention, and for convenience, all CUBI metadata are organized in form of a `pyproject.toml` file
containing a minimal amount of descriptive entries. This file must be located at the top-level of the
respective repository. The "hierarchy" in these files is as follows:

1. include [Python tool settings](tomls/tool/pyproject.toml) for coherent formatting of Python code
    - if the repository does not contain any Python code, this may be omitted
2. include [the CUBI metadata information](pyproject.toml), i.e., the top-level `pyproject.toml` in this repository
3. include specific metadata...
    - ...for a [project repository](tomls/cubi/project/pyproject.toml)
    - ...for a [workflow template repository](tomls/cubi/workflow/template/pyproject.toml)
    - ...for a [workflow repository](tomls/cubi/workflow/pyproject.toml)

As a reminder, read the development guidelines to learn about key characteristics
of workflows and projects, and naming conventions:

[CUBI dev process in the knowledge base](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Dev-process#repository-types)

[CUBI naming conventions in the knowledge base](https://github.com/core-unit-bioinformatics/knowledge-base/wiki/Naming-and-style#naming-repositories)

# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
