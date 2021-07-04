" Prevent loading the plugin multiple times
if exists('g:livedoc_loaded')
    finish
endif
let g:livedoc_loaded = 1

if !has("python3")
    echo "vim has to be compiled with +python3 to run this"
    finish
endif

if !exists('g:livedoc_api_key')
    echo "No Livedoc API key set"
    finish
endif

let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
sys.path.insert(0, plugin_root_dir)
import livedoc
EOF

function s:docgen_cb(channel, msg)
    python3 livedoc.docgen_cb()
endfunction

function! UpdateLivedoc()
    let job = job_start(["/usr/bin/python3", s:plugin_root_dir . "/livedoc_proxy.py", expand('%:p')], {
                \ 'in_io': 'buffer',
                \ 'in_buf': bufnr('%'),
                \ 'out_cb': function('s:docgen_cb'),
                \ 'env': {'API_KEY': g:livedoc_api_key}
                \ })
endfunction

command! -nargs=0 UpdateLivedoc call UpdateLivedoc()


function! SaveLivedoc()
    python3 livedoc.persist()
endfunction

command! -nargs=0 SaveLivedoc call SaveLivedoc()

autocmd BufWritePost * SaveLivedoc
