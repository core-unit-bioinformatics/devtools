# CUBI tools

This repository is a collection of helper tools and useful scipts for internal and
external use. The CUBI tools are implemented with minimal dependencies outside of the
Python standard library (Python v3.9). Currently, the only non-standard package is `toml`
(`python3-toml`), which must be available to execute any CUBI tool.

# Available tools

- `auto_git.py`: automate init, clone and normalization of git repositories. Some features require
a so-called identity file to work. See the [`auto_git` documentation](#auto_git) for details.

# Tool documentation

## auto_git

### Purpose

Automates configuring git repositories on your machine according
to CUBI standards (see [CUBI knowledge base](https://github.com/core-unit-bioinformatics/knowledge-base/wiki)).

### Requirements: identity file(s)

Configuring a git repository requires setting a user name and email address before commits to the repo can be made.
The `auto_git.py` script extracts that info from local files. Those files are referred to as "identity files".
Identity files are simple text files with two lines: line one specifies the user name and line
two specifies the email address to be used for the following git config operations of the repo:

```bash
git config user.name <USERNAME>
git config user.email <EMAIL>
```

One identity file per remote (such as `github`) must exist. The filename must be `<REMOTE>.id`, e.g. `github.id`, and the identity
file(s) must be stored in a folder that can be set via the `--git-identities` parameter of the `auto_git.py` script. By default, this folder is assumed to be `$HOME/.identities`.


# Citation

If not indicated otherwise above, please follow [these instructions](CITATION.md) to cite this repository in your own work.
