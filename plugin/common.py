#@livedoc
from typing import List, Optional

import logging
import os
import pathlib
import subprocess


NULL = open('/dev/null', 'w')


# Copypasta from git post-merge.py
# TODO: have a proper python library for this, or a common file that's symlinked
def get_repo_root(fn: str) -> Optional[pathlib.Path]:
    """
    @startdoc
    @overview This code defines a function that takes a git repository as input and returns the root of the git repository.
    @end
    """
    try:
        root = subprocess.check_output([
            'git',
            '-C', os.path.dirname(fn),
            'rev-parse',
            '--show-toplevel',
        ], stderr=NULL).decode('utf-8').strip()
    except:
        return None

    logging.debug(f'Got root {root}')
    return pathlib.Path(root)


def get_origin_url(repo: str) -> str:
    """
    @startdoc
    @overview This code gets the origin url for a repository and logs it.
    @details This code defines a function that gets the origin url for a repository.
    @end
    """
    origin = subprocess.check_output([
        'git',
        '-C', repo,
        'config',
        '--get', 'remote.origin.url',
    ], stderr=NULL).decode('utf-8').strip()
    logging.debug(f'Got origin {origin}')
    return origin


def get_current_branch(repo: str) -> str:
    """
    @startdoc
    @overview This code gets the current branch of a git repository and logs it.
    @details This code defines a function that gets the current branch of a git repository.
    @end
    """
    branch = subprocess.check_output([
        'git',
        '-C', repo,
        'rev-parse', '--abbrev-ref', 'HEAD',
    ], stderr=NULL).decode('utf-8').strip()
    logging.debug(f'Got current branch {branch}')
    return branch


def get_last_commit_id(repo: str) -> str:
    """
    @startdoc
    @overview This code gets the last commit ID from a git repository.
    @details This code gets the last commit ID from a git repository.
    @end
    """
    commit = subprocess.check_output([
        'git',
        '-C', repo,
        'rev-parse', 'HEAD',
    ], stderr=NULL).decode('utf-8').strip()
    logging.debug(f'Got last commit {commit}')
    return commit


def get_files_in_commit(repo: str, commit: str) -> List[str]:
    """
    @startdoc
    @overview This function gets the files in the last commit.
    @details This code gets the files in the last commit.
    @end
    """
    files = subprocess.check_output([
        'git',
        '-C', repo,
        'diff',
        '--name-only',
        commit + '~', commit,
    ], stderr=NULL).decode('utf-8').split('\n')[:-1]
    logging.debug(f'Got files in last commit: {files}')
    return files


def is_file_tracked(repo: str, fn: str) -> bool:
    """
    @startdoc
    @overview This code checks if a file is tracked in a git repository.
    @details This code is a function that checks if a file is tracked by git.
    @end
    """
    out = subprocess.check_output([
        'git',
        '-C', repo,
        'ls-files',
        fn,
    ], stderr=NULL).decode('utf-8').strip()
    logging.debug(f'Got ls-files output {out}')
    return out != ''
