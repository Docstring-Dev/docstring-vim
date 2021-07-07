import json
import logging
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.append(str(pathlib.Path(__file__).parent / 'vendor'))

from realtime_py.connection import Socket

from common import get_repo_root, get_current_branch, is_file_tracked


API_ENDPOINT = 'https://app.livedoc.ai/api/integrations/vscode/docs/create_async'
WS_ENDPOINT = 'wss://app.livedoc.ai/socket/websocket'
if 'LIVEDOC_DEV' in os.environ:
    API_ENDPOINT = 'http://localhost:4000/api/integrations/vscode/docs/create_async'
    WS_ENDPOINT = 'ws://localhost:4000/socket/websocket'

API_KEY = os.environ['API_KEY']

if __name__ == "__main__":
    cur_file = sys.argv[1]
    contents = sys.stdin.read()

    repo_root = get_repo_root(cur_file)

    if repo_root is None:
        print(json.dumps({
            'type': 'error',
            'level': logging.INFO,
            'message': f'Livedoc: Not persisting file {cur_file}: not in a git repository',
        }))
        sys.exit(0)

    relative_file = pathlib.Path(cur_file).relative_to(repo_root)
    branch = get_current_branch(str(repo_root))
    #repo_origin = get_origin_url(str(repo_root))
    repo = repo_root.name

    if relative_file.name.lower() != 'readme.md' and '@livedoc' not in contents:
        print(json.dumps({
            'type': 'error',
            'level': logging.INFO,
            'message': f'Livedoc: Not persisting file {relative_file}: "@livedoc" not in file',
        }))
        sys.exit(0)

    if not is_file_tracked(str(repo_root), str(relative_file)):
        print(json.dumps({
            'type': 'error',
            'level': logging.INFO,
            'message': f'Livedoc: Not persisting file {relative_file}: not tracked by git',
        }))
        sys.exit(0)

    s = Socket(f"{WS_ENDPOINT}?token={API_KEY}")
    s.connect()

    post_data = json.dumps({
        'content': contents,
        'filename': relative_file.name,
        'path': str(relative_file.parent),
        'branch': branch,
        'repo': repo,
    }).encode('utf-8')

    req = urllib.request.Request(API_ENDPOINT)
    req.add_header('User-Agent', 'livedoc-vim/0.1 (https://github.com/Whize-Co/livedoc-vim)')
    req.add_header('authorization', f'Bearer {API_KEY}')
    req.add_header('content-type', 'application/json')
    req.add_header('content-length', str(len(post_data)))

    try:
        resp = urllib.request.urlopen(req, post_data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(json.dumps({
            'type': 'error',
            'level': logging.ERROR,
            'message': f'Livedoc: Error generating: {body}',
        }))
        sys.exit(0)

    j = json.loads(resp.read().decode('utf-8'))

    print(json.dumps({
        'type': 'init',
        'data': j,
    }))

    def cb(payload):
        print(json.dumps({
            'type': 'token',
            'topic': j['topic'],
            'data': payload,
        }))

    chan = s.set_channel(j['topic'])
    chan.join().on("new_token", cb)

    s.listen()
