#!/usr/bin/env python3
"""Typeset exact log excerpts; these images are not terminal screenshots."""
from pathlib import Path
import hashlib
import json
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
def font(size,mono=True):
    paths=([r'C:\Windows\Fonts\CascadiaMono.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'] if mono else
           [r'C:\Windows\Fonts\segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for path in paths:
        if Path(path).is_file(): return ImageFont.truetype(path,size)
    return ImageFont.load_default(size=size)
body_font=font(26)
title_font=font(30,False)
small_font=font(20,False)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

specs=[
 ('01-grade.png','Official grade | 30 / 30','grade.txt',lambda s:bool(s.strip()),'make grade; original three scoring tests'),
 ('02-extra.png','Supplemental RV64 tests | 128 MiB','extra-rv64.txt',lambda s:s.startswith('[Extra'),'Normal shared-root path; test copy'),
 ('03-gdb.png','Guest GDB | First thread entry','guest-gdb.txt',lambda s:s.startswith('CHECKPOINT '),'Normal ELF; ten observed checkpoints'),
 ('04-fixed-stack.png','Fixed stack experiment | Separate variant','fixed-stack.txt',lambda s:s.startswith('[Fixed stack'),'Distinct physical stacks; guard access faults'),
]
manifest=[]
for filename,title,source,select,footer in specs:
    source_path=ROOT/'evidence'/source
    original=[s for s in source_path.read_text(encoding='utf-8').splitlines() if select(s)]
    assert original
    lines=[]
    for line in original:
        lines.extend(textwrap.wrap(line,width=88,subsequent_indent='  ',replace_whitespace=False,drop_whitespace=False) or [''])
    dummy=ImageDraw.Draw(Image.new('RGB',(1,1)))
    width=max(920,int(max(dummy.textlength(line,font=body_font) for line in lines))+80)
    height=132+len(lines)*39+65
    canvas=Image.new('RGB',(width,height),'white')
    draw=ImageDraw.Draw(canvas)
    draw.text((36,26),title,font=title_font,fill='#171717')
    draw.line((36,82,width-36,82),fill='#a8a8a8',width=1)
    for i,line in enumerate(lines): draw.text((36,106+i*39),line,font=body_font,fill='#222222')
    draw.line((36,height-64,width-36,height-64),fill='#c8c8c8',width=1)
    draw.text((36,height-48),'Typeset log excerpt | '+footer,font=small_font,fill='#565656')
    target=ROOT/'images'/filename
    canvas.save(target)
    manifest.append(dict(file=filename,width=width,height=height,sha256=sha(target),evidence=source,source_sha256=sha(source_path),selected_lines=original))
(ROOT/'evidence/images.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='selected_lines'} for r in manifest],indent=2))
