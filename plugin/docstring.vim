" Prevent loading the plugin multiple times
if exists('g:docstring_loaded')
    finish
endif
let g:docstring_loaded = 1

if !has("python3")
    echo "vim has to be compiled with +python3 to run this"
    finish
endif

if !exists('g:docstring_api_key')
    echo "No Docstring API key set"
    finish
endif

let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
sys.path.insert(0, plugin_root_dir)
import docstring
EOF

function s:docgen_cb(channel, msg)
    python3 docstring.docgen_cb()
endfunction

function! UpdateDocstring()
    let job = job_start(["/usr/bin/python3", s:plugin_root_dir . "/docstring_proxy.py", expand('%:p')], {
                \ 'in_io': 'buffer',
                \ 'in_buf': bufnr('%'),
                \ 'out_cb': function('s:docgen_cb'),
                \ 'env': {'API_KEY': g:docstring_api_key}
                \ })
endfunction

command! -nargs=0 UpdateDocstring call UpdateDocstring()


function! SaveDocstring()
    python3 docstring.persist()
endfunction

command! -nargs=0 SaveDocstring call SaveDocstring()

autocmd BufWritePost * SaveDocstring
