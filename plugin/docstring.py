#@docstring
import json
import logging
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
import vim

from common import get_repo_root, get_current_branch, is_file_tracked


if (sys.version_info < (3, 6)):
    logging.error(f'Unsupported version of Python')
    sys.exit(1)


API_HOST = 'https://app.docstring.dev'
if 'DOCSTRING_DEV' in os.environ:
    API_HOST = 'http://localhost:4000'

API_ENDPOINT = API_HOST + '/api/integrations/vscode'
API_KEY = vim.eval('g:docstring_api_key')

DOC_BEFORE = "BEFORE"


def verbose():
    """
    @startdoc
    Determines if verbose logs should be emitted
    @end
    """
    return bool(int(vim.eval('get(g:, "docstring_verbose", 0)')))


def persist():
    """
    @startdoc
    Persists the contents of the current buffer to Docstring
    @end
    """
    contents = '\n'.join(vim.current.buffer)

    cur_file = vim.current.buffer.name

    if not pathlib.Path(cur_file).exists():
        return

    repo_root = get_repo_root(cur_file)

    if repo_root is None:
        if verbose():
            print(f'Docstring: Not persisting file {cur_file}: not in a git repository')
        return

    relative_file = pathlib.Path(cur_file).relative_to(repo_root)
    branch = get_current_branch(str(repo_root))
    #repo_origin = get_origin_url(str(repo_root))
    repo = repo_root.name

    if relative_file.name.lower() != 'readme.md' and '@docstring' not in contents:
        if verbose():
            print(f'Docstring: Not persisting file {relative_file}: "@docstring" not in file')
        return

    if not is_file_tracked(str(repo_root), str(relative_file)):
        if verbose():
            print(f'Docstring: Not persisting file {relative_file}: not tracked by git')
        return

    post_data = json.dumps({
        'content': '\n'.join(vim.current.buffer),  # TODO: figure out line ending from mode?
        'filename': relative_file.name,
        'path': str(relative_file.parent),
        'branch': branch,
        'repo': repo,
    }).encode('utf-8')

    if relative_file.name.lower() == 'readme.md':
        endpoint = API_ENDPOINT + '/readme/persist'
    else:
        endpoint = API_ENDPOINT + '/docs/persist'

    req = urllib.request.Request(endpoint)
    req.add_header('User-Agent', 'docstring-vim/0.1 (https://github.com/Whize-Co/docstring-vim)')
    req.add_header('authorization', f'Bearer {API_KEY}')
    req.add_header('content-type', 'application/json')
    req.add_header('content-length', str(len(post_data)))

    # Timeout so that we don't hold up editor operations if hitting the API is slow
    try:
        urllib.request.urlopen(req, post_data, timeout=5)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f'Docstring: Error saving: {body}')
        return
    except urllib.error.URLError as e:
        return


async_state = {}


def docgen_cb():
    """
    @startdoc
    Callback handler for async document generation.
    Called each time a line from docstring_proxy.py is received by vim.
    @end
    """
    payload = json.loads(vim.eval("a:msg"))
    if payload['type'] == 'init':
        scopes = payload['data']['scopes']
        template = payload['data']['template']
        position = payload['data']['position']

        scopesByDocStart = {}
        templateLength = len(template.split("\n"))

        for i, scope in enumerate(scopes):
            # -1 because vim line numbers are 0-indexed, but we get 1-indexed from API
            scopeEnd = scope['range']['end']['line'] - 1

            previousTemplateadjustment = templateLength * i;

            whitespace = ''

            # docsStart is the line number _before_ which the doc should be added
            # meaning the docs will then be on that line
            if position == DOC_BEFORE:
                scopeStart = scope['range']['start']['line'] - 1
                docsStart = scopeStart
                whitespace = re.match(r'\s*', vim.current.buffer[scopeStart+previousTemplateadjustment]).group()
            else:
                scopeBodyStart = scope['range']['body_start']['line'] - 1
                docsStart = scopeBodyStart

                # indent to the indentation of the first, non-empty line in the body of the scope
                for line in vim.current.buffer[scopeBodyStart+previousTemplateadjustment:scopeEnd+previousTemplateadjustment+1]:
                    if line.strip() != '':
                        whitespace = re.match(r'\s*', line).group()
                        break

            scopesByDocStart[docsStart] = {
                'scope': scope,
                'scopesAfter': [],
                'adjustedOverviewStart': docsStart + 2,
                'adjustedDetailsStart': docsStart + 3,
                'adjustedDocEnd': docsStart + 4,
            }

            tabAdjustedTemplate = map(lambda line: whitespace + line, template.split("\n"))

            vim.current.buffer.append(list(tabAdjustedTemplate), docsStart + previousTemplateadjustment)

            for j in range(len(scopes) - 1, i, -1):
                scopeAfter = scopes[j]
                if position == DOC_BEFORE:
                    scopeAfterDocsStart = scopeAfter['range']['start']['line'] - 1
                else:
                    scopeAfterDocsStart = scopeAfter['range']['body_start']['line'] - 1
                scopesByDocStart[docsStart]["scopesAfter"].append(scopeAfterDocsStart)

        for thing in scopesByDocStart.values():
            for scopeLine in thing['scopesAfter']:
                scopesByDocStart[scopeLine]['adjustedOverviewStart'] += templateLength
                scopesByDocStart[scopeLine]['adjustedDetailsStart'] += templateLength
                scopesByDocStart[scopeLine]['adjustedDocEnd'] += templateLength

        async_state[payload['data']['topic']] = {
            'position': position,
            'scopesByDocStart': scopesByDocStart,
        }

    elif payload['type'] == 'token':
        data = payload['data']

        position = async_state[payload['topic']]['position']
        scopesByDocStart = async_state[payload['topic']]['scopesByDocStart']

        payloadScope = data['scope']

        if position == DOC_BEFORE:
            docsStart = payloadScope['range']['start']['line'] - 1
        else:
            docsStart = payloadScope['range']['body_start']['line'] - 1

        scope = scopesByDocStart[docsStart]
        docsEndLine = scope["adjustedDocEnd"]

        if data['type'] == "@overview":
            insertPosition = scope["adjustedDetailsStart"] - 1
        else:
            insertPosition = docsEndLine - 1

        if data['text'] == '\n':
            return

        vim.current.buffer[insertPosition] += data['text']

    elif payload['type'] == 'error':
        if verbose() or payload['level'] >= logging.ERROR:
            print(payload['message'])
