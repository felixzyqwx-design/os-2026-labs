"""Render report figures from attached actual logs and GDB data (requires Pillow)."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--font',type=Path,help='Chinese-capable TrueType/OpenType font')
parser.add_argument('--mono-font',type=Path)
args = parser.parse_args()
report = Path(__file__).resolve().parents[1]
evidence = report/'evidence'
images = report/'images'
images.mkdir(exist_ok=True)
def find_font(explicit, candidates):
    paths = ([explicit] if explicit else [])+[Path(x) for x in candidates]
    for path in paths:
        if path.exists():
            return path
    raise SystemExit('Font missing; pass --font and --mono-font.')
chinese = find_font(args.font,['C:/Windows/Fonts/msyh.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'])
mono = find_font(args.mono_font,['C:/Windows/Fonts/consola.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'])
def font(size,code=False):
    return ImageFont.truetype(str(mono if code else chinese),size)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):
    return json.loads((evidence/name).read_text(encoding='utf-8'))
meta = []
def canvas(title,subtitle,height):
    im = Image.new('RGB',(1680,height),'#ffffff')
    draw = ImageDraw.Draw(im)
    draw.rectangle((0,0,1679,7),fill='#245e86')
    draw.text((46,34),title,font=font(35),fill='#182d3d')
    draw.text((48,91),subtitle,font=font(22),fill='#52616d')
    draw.line((46,137,1634,137),fill='#ced7de',width=2)
    return im,draw
def put(draw,xy,value,size=25,code=False,fill='#243440'):
    box=draw.textbbox(xy,value,font=font(size,code))
    assert box[0]>=0 and box[2]<1640, ('Text overflow',value,box)
    draw.text(xy,value,font=font(size,code),fill=fill)
def save(im,name,sources,extra=None):
    path=images/name
    im.save(path,optimize=True)
    meta.append(dict(image=name,width=im.width,height=im.height,sha256=sha(path),
        kind='typeset actual evidence, not a terminal screenshot',
        sources={x:sha(evidence/x) for x in sources},details=extra))

grade=(evidence/'grade.txt').read_text().splitlines()
selected=[x for x in grade if ': PASS (' in x or x.startswith('Total Score:')]
assert len(selected)==4 and selected[-1]=='Total Score: 100/100'
im,draw=canvas('官方评分结果','本次 grade.txt 的原始结果行摘录排版',450)
for i,line in enumerate(selected):
    put(draw,(50,171+i*58),line,size=27,code=True,
        fill='#195d43' if i==3 else '#243440')
save(im,'01-grade.png',['grade.txt'],dict(selected_lines=selected))

boot=(evidence/'boot.txt').read_text().splitlines()
start=next(i for i,x in enumerate(boot) if x.startswith('memory management:'))
selected=boot[start:]
assert selected.count('100 ticks')==10
result=next(x for x in load('results.json')['workspace'] if x['entry']=='qemu')
assert result['passed'] and result['exit']==0 and result['tick_lines']==10
im,draw=canvas('默认时钟运行与关机','boot.txt 末段原始日志排版；下方状态来自运行器记录',850)
for i,line in enumerate(selected):
    put(draw,(50,167+i*34),line,size=22,code=True)
draw.line((48,752,1632,752),fill='#ced7de',width=2)
put(draw,(50,779),'运行器记录：100 ticks 共 10 行；QEMU 退出码 0。',size=26,fill='#195d43')
save(im,'02-timer.png',['boot.txt','results.json'],dict(selected_lines=selected,workspace_result=result))

exc=load('gdb-exceptions.json')
timer=load('gdb-timer.json')
assert len(exc)==4 and len(timer)==2
assert [x['instruction_bytes'] for x in exc]==[2,4,2,4]
assert all(x['passed'] and x['gpr_checked']==32 for x in exc+timer)
im,draw=canvas('GDB 观察的 Trap 返回现场','由本次 observations 数据排版；完整地址、状态与 frame 见随附 JSON',790)
xs=[48,230,365,730,1110,1310]
headers=['原因','编码字节','sepc（进入）','sepc（返回）','GPR 槽','结果']
draw.rectangle((46,159,1634,209),fill='#eef3f6')
for x,label in zip(xs,headers):
    put(draw,(x,168),label,size=23)
for i,row in enumerate(exc+timer):
    y=230+i*61
    label=['断点 1','断点 2','非法指令 1','非法指令 2','时钟 1','时钟 2'][i]
    values=[label,str(row['instruction_bytes']) if i<4 else '—',
        row['epc_before'],row['epc_after'],str(row['gpr_checked']),'PASS']
    for j,(x,value) in enumerate(zip(xs,values)):
        put(draw,(x,y),value,size=24,code=j in [2,3,4,5],
            fill='#195d43' if j==5 else '#243440')
    draw.line((46,y+45,1634,y+45),fill='#e3e9ee')
put(draw,(48,633),'时钟中断前后 sepc 不变；异常分别跳过 2 / 4 / 2 / 4 字节。',size=25)
put(draw,(48,685),'时钟 sstatus：0x8000000200006120 → 0x8000000200006022',size=24)
put(draw,(48,733),'六次返回均检查 sp、frame、CSR、GPR 与 S 态返回。',size=23,fill='#52616d')
save(im,'03-gdb.png',['gdb-exceptions.json','gdb-timer.json'],dict(rows=exc+timer))
(evidence/'image-sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Rendered 3 figures from actual logs and GDB observations.')
