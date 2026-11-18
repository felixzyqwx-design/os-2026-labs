#!/usr/bin/env python3
"""Check portable links, evidence versions and images; does not rerun kernel tests."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import struct

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'report'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check-recorded-elf', action='store_true',
                    help='also require the exact ELF used in the recorded GDB session')
args=parser.parse_args()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
result=load(REPORT/'evidence/results.json')
for rel,digest in result['source_files_sha256'].items():
    assert sha(ROOT/rel)==digest, 'Source changed: '+rel

links=0
for document in [ROOT/'README.md',REPORT/'report.md',REPORT/'prompt.md']:
    text=document.read_text(encoding='utf-8')
    assert '\ufffd' not in text and '\0' not in text
    assert sum(line.startswith('```') for line in text.splitlines())%2==0,document
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
        if target.startswith(('http://','https://','#')): continue
        assert (document.parent/target.split('#')[0]).resolve().is_file(),(document,target)
        links+=1
    width=None
    fenced=False
    for line in text.splitlines():
        if line.startswith('```'): fenced=not fenced
        if not fenced and line.startswith('|'):
            count=len(re.split(r'(?<!\\)\|',line))-2
            if width is None: width=count
            assert count==width,(document,line)
        else: width=None
    assert not re.search(r'[A-Z]:[\\/]|/mnt/[a-z]/|答辩准备|会话交接',text),document

prompt=(REPORT/'prompt.md').read_text(encoding='utf-8')
blocks=re.split(r'^## (?=P\d+-[ITA]：)',prompt,flags=re.M)[1:]
assert len(blocks)==16
for block in blocks:
    for label in ['[PROMPT]','[RELY]','[GUARANTEE]','[SPECIFICATION]']:
        assert block.count(label)==1,(block.splitlines()[0],label)
    assert 'Pre-Condition' in block and 'Post-Condition' in block
    assert block.index('[PROMPT]')<block.index('[RELY]')<block.index('[GUARANTEE]')<block.index('[SPECIFICATION]')
for name in ['page_insert','page_remove','alloc_proc','proc_init','kernel_thread','do_fork','copy_thread','copy_mm','cpu_idle','schedule','proc_run','switch_to']:
    assert name in prompt

for name,record in result['excerpts'].items():
    assert sha(REPORT/'evidence'/name)==record['excerpt_sha256'],name
images=load(REPORT/'evidence/images.json')
used=re.findall(r'!\[[^\]]*\]\(images/([^)]+)\)',(REPORT/'report.md').read_text(encoding='utf-8'))
assert len(used)==4 and set(used)=={r['file'] for r in images}
for image in images:
    path=REPORT/'images'/image['file']
    assert sha(path)==image['sha256'],path
    data=path.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II',data[16:24])==(image['width'],image['height'])
    source=REPORT/'evidence'/image['evidence']
    assert sha(source)==image['source_sha256']
    text=source.read_text(encoding='utf-8')
    assert all(line in text for line in image['selected_lines'])
assert result['official_grade']['score']==result['official_grade']['total']==30
assert all(row['passed'] for row in result['memory_matrix'])
assert len(result['synthetic_boundaries'])==7 and all(row['passed'] for row in result['synthetic_boundaries'])
kernel=ROOT/'code/bin/kernel'
elf=None
if kernel.exists():
    digest=sha(kernel)
    elf=dict(sha256=digest, matches_recorded_gdb_elf=digest==result['guest_gdb']['normal_elf_sha256'])
# Debug information embeds the build directory. Source checks above apply to
# any checkout; exact historical ELF identity is an explicit, separate check.
if args.check_recorded_elf:
    assert elf is not None and elf['matches_recorded_gdb_elf'], 'Not the recorded GDB ELF'
for script in (REPORT/'scripts').glob('*.py'): ast.parse(script.read_text(encoding='utf-8'))
print(json.dumps(dict(materials_static_check='PASS',source_files=len(result['source_files_sha256']),local_links=links,
    four_part_prompts=len(blocks),images=len(images),normal_elf=elf,
    kernel_tests='recorded prior RV64 runs; not rerun by this checker'),ensure_ascii=False,indent=2))
