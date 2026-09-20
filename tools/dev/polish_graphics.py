"""Incremental, reproducible graphics fixes on top of the v1.0.1 Korean ROM.

Only graphics are replaced. Each checkpoint includes a ROM, a BPS from the
original dump, extracted resources, verification results and before/after art.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ndsrom import Rom
import lz
import bps
import fix_digest

GFX_NAMES = ('subtask_us_en.cmp', 'zeldat_us_en.bin')
MAP_LAYOUT = {(x, y): t for x, y, t in [
    (0, 8, 5), (8, 0, 2), (8, 8, 6), (16, 0, 3), (16, 8, 7),
    (24, 0, 8), (24, 8, 12), (32, 0, 9), (32, 8, 13),
    (40, 0, 10), (40, 8, 14), (48, 0, 11), (48, 8, 15),
    (56, 0, 16), (56, 8, 20), (64, 0, 17), (64, 8, 21),
    (72, 0, 18), (72, 8, 22), (80, 0, 19), (80, 8, 23),
    (88, 0, 24), (88, 8, 28), (96, 0, 25), (96, 8, 29),
    (104, 0, 26), (104, 8, 30), (112, 0, 27), (112, 8, 31)]}
MAP_PALETTE = [(89,235,40),(130,73,8),(154,97,8),(178,121,8),
    (203,138,8),(219,170,8),(235,186,8),(243,219,8),(251,235,0),
    (251,251,0),(251,251,48),(251,251,138),(251,251,186),(251,251,251)]


def unpack4(raw):
    return [v for b in raw for v in (b & 15, b >> 4)]


def pack4(pixels):
    return bytes(pixels[i] | pixels[i+1] << 4 for i in range(0,len(pixels),2))


def zentries(data):
    count = struct.unpack_from('<I',data)[0] // 8
    entries = []
    for i in range(count):
        off, size = struct.unpack_from('<II',data,i*8)
        blob = data[off:off+(size & 0x7fffffff)]
        entries.append((blob, bool(size >> 31)))
    return entries


def rawentry(entry):
    blob, compressed = entry
    return lz.decompress(blob) if compressed else blob


def zpack(entries):
    table, body = bytearray(), bytearray()
    for blob, compressed in entries:
        table += struct.pack('<II',len(entries)*8+len(body),len(blob)|(0x80000000 if compressed else 0))
        body += blob
    return bytes(table+body)


def map_index(x, y):
    return MAP_LAYOUT[(x//8*8,y//8*8)]*64+(y%8)*8+x%8


def map_image(raw):
    pixels = unpack4(raw)
    im = Image.new('RGB',(128,16),'#333943')
    for (bx,by),ti in MAP_LAYOUT.items():
        for y in range(8):
            for x in range(8):
                v = pixels[ti*64+y*8+x]
                im.putpixel((bx+x,by+y),MAP_PALETTE[v] if v<len(MAP_PALETTE) else (255,0,255))
    return im


def comparison(rows, path, title, scale=4, note='실제 롬에서 추출한 그래픽 재구성 · 게임 실행 화면은 아님'):
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',18)
    small = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',14)
    width = max(2*max(a.width,b.width)*scale+64 for _,a,b in rows)
    width = max(width,750)
    height = 94 + sum(max(a.height,b.height)*scale+44 for _,a,b in rows)
    out = Image.new('RGB',(width,height),'#20242c');d=ImageDraw.Draw(out)
    d.text((18,10),title,font=font,fill='white')
    d.text((18,40),note,font=small,fill='#aebcd0')
    d.text((18,66),'BEFORE · 수정 전',font=small,fill='#f2c977')
    d.text((width//2+10,66),'AFTER · 수정 후',font=small,fill='#86d9ad')
    y=94
    for label,a,b in rows:
        d.text((18,y),label,font=small,fill='white');y+=24
        for x,im in [(18,a),(width//2+10,b)]:
            out.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(x,y))
        y+=max(a.height,b.height)*scale+20
    out.save(path)


class SubTiles:
    def __init__(self, compressed):
        self.raw = bytearray(lz.decompress(compressed))
        count = struct.unpack_from('<I',self.raw)[0]//4
        self.offsets = struct.unpack_from('<%dI'%count,self.raw)
        self.sheets = {}
        for k in range(5):
            off=self.offsets[k]
            size=struct.unpack_from('<I',self.raw,off+0x28)[0]
            self.sheets[k]=unpack4(self.raw[off+0x30:off+0x30+size])

    def get(self,k,x,y):
        return self.sheets[k][(y//8*32+x//8)*64+(y%8)*8+x%8]

    def set(self,k,x,y,v):
        self.sheets[k][(y//8*32+x//8)*64+(y%8)*8+x%8]=v

    def image(self,k,rect):
        x0,y0,x1,y1=rect
        im=Image.new('RGB',(x1-x0+1,y1-y0+1))
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):im.putpixel((x-x0,y-y0),(self.get(k,x,y)*17,)*3)
        return im

    def packed(self):
        for k,pixels in self.sheets.items():
            off=self.offsets[k]+0x30;data=pack4(pixels)
            self.raw[off:off+len(data)]=data
        compressed=lz.compress_lz11(bytes(self.raw))
        assert lz.decompress(compressed)==bytes(self.raw)
        return compressed


def text_mask(text, width, height, maximum=14, outlined=True):
    padding=1 if outlined else 0
    for size in range(maximum,7,-1):
        font=ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf',size)
        l,t,r,b=font.getbbox(text)
        if r-l+padding*2<=width and b-t+padding*2<=height:break
    else:raise ValueError('Text does not fit: '+text)
    im=Image.new('1',(r-l+padding*2,b-t+padding*2));d=ImageDraw.Draw(im)
    d.fontmode='1';d.text((padding-l,padding-t),text,font=font,fill=1)
    return im,size


def edit_text(sheets,k,rect,text,background,fill=15,outline=1,maximum=14):
    x0,y0,x1,y1=rect
    mask,size=text_mask(text,x1-x0+1,y1-y0+1,maximum,outline is not None)
    # Snapshot the profile before mutation, including sample columns.
    bg=[background(y) if callable(background) else background for y in range(y0,y1+1)]
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):sheets.set(k,x,y,bg[y-y0])
    ox=x0+(x1-x0+1-mask.width)//2;oy=y0+(y1-y0+1-mask.height)//2
    for y in range(mask.height):
        for x in range(mask.width):
            if mask.getpixel((x,y)):sheets.set(k,ox+x,oy+y,fill)
            elif outline is not None and any(0<=x+dx<mask.width and 0<=y+dy<mask.height and mask.getpixel((x+dx,y+dy)) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]):
                sheets.set(k,ox+x,oy+y,outline)
    return {'sheet':k,'rect':rect,'text':text,'font_size':size,'glyph_size':mask.size}


def background_profile(sheets,k,rect):
    # Whole columns avoid choosing bright glyph pixels on densely filled rows.
    x0,y0,x1,y1=rect
    columns=Counter(tuple(sheets.get(k,x,y) for y in range(y0,y1+1)) for x in range(x0,x1+1))
    profile,count=columns.most_common(1)[0]
    assert count>=3, 'No reliable blank background columns'
    return lambda y:profile[y-y0]


def stage02a(resources, output):
    sheets=SubTiles(resources['subtask_us_en.cmp']);rows=[];edits=[]
    for label,rect,text in [
        ('파일 복사 안내',(0,80,159,95),'어디에 복사할까요?'),
        ('파일 삭제 확인',(0,96,159,111),'정말 삭제할까요?')]:
        before=sheets.image(2,rect)
        edits.append(edit_text(sheets,2,rect,text,background_profile(sheets,2,rect),maximum=13))
        rows.append((label,before,sheets.image(2,rect)))
    resources['subtask_us_en.cmp']=sheets.packed()
    comparison(rows,output/'before_after.png','02-A · 파일 복사·삭제 안내',scale=3,
               note='실제 롬 그래픽 · 식별용 회색조 · 게임 내 색상은 기존 팔레트 유지')
    return {'edits':edits}


def stage02b(resources, output):
    sheets=SubTiles(resources['subtask_us_en.cmp']);rows=[];edits=[]
    # The two UI copies and the packed in-game sprite have identical Back
    # pixels, but the in-game top/bottom pieces occupy nonadjacent tile slots.
    back_before=[sheets.get(1,x,y) for y in range(20,32) for x in range(104,136)]
    specs=[
        ('작은 시작 버튼',1,(201,3,242,15),'시작',lambda y:sheets.get(1,244,y),15,None,12,(184,0,255,23)),
        ('확인 버튼',1,(201,35,242,47),'확인',lambda y:sheets.get(1,244,y),15,None,12,(184,32,255,55)),
        ('뒤로 · 메뉴 사본 1',1,(104,20,135,31),'뒤로',0,14,10,11,(104,8,135,31)),
        ('뒤로 · 메뉴 사본 2',2,(80,228,111,239),'뒤로',0,14,10,11,(80,216,111,239)),
        ('나가기',2,(199,215,244,233),'나가기',lambda y:sheets.get(2,247,y),15,None,14,(184,208,255,239)),
        ('대기 표시 · 사본 1',1,(108,152,223,167),'잠시 기다려 주세요',0,15,1,12,(104,152,227,167)),
        ('대기 표시 · 사본 2',2,(0,112,159,127),'잠시 기다려 주세요',0,15,1,12,(0,112,159,127)),
        ('색 선택 · 작은 변형',1,(0,160,71,175),'색 선택',0,6,1,12,(0,160,71,175)),
        ('색 선택 · 큰 변형',1,(112,176,207,191),'색 선택',0,6,4,12,(112,176,207,191)),
    ]
    for label,k,rect,text,bg,fill,outline,size,crop in specs:
        before=sheets.image(k,crop)
        if label=='작은 시작 버튼':
            # The English g descender sits below the Korean glyph box.
            for y in range(16,19):
                value=sheets.get(1,244,y)
                for x in range(201,243):sheets.set(1,x,y,value)
        edits.append(edit_text(sheets,k,rect,text,bg,fill,outline,size))
        rows.append((label,before,sheets.image(k,crop)))
    entries=zentries(resources['zeldat_us_en.bin']);raw=rawentry(entries[16]);pixels=unpack4(raw)
    def back_idx(x,y):
        return (180+x//8)*64+(y+4)*8+x%8 if y<4 else (184+x//8)*64+(y-4)*8+x%8
    assert [pixels[back_idx(x,y)] for y in range(12) for x in range(32)]==back_before
    before=Image.new('RGB',(32,12));after=before.copy()
    for y in range(12):
        for x in range(32):
            i=back_idx(x,y);before.putpixel((x,y),(pixels[i]*17,)*3)
            pixels[i]=sheets.get(1,x+104,y+20)
            after.putpixel((x,y),(pixels[i]*17,)*3)
    newraw=pack4(pixels);blob=lz.compress_lz11(newraw)
    assert lz.decompress(blob)==newraw
    entries[16]=(blob,True);resources['zeldat_us_en.bin']=zpack(entries)
    rows.append(('뒤로 · 게임 내 별도 사본',before,after))
    resources['subtask_us_en.cmp']=sheets.packed()
    comparison(rows,output/'before_after.png','02-B · 공통 버튼·대기·색 선택',scale=3,
               note='실제 롬 그래픽 · 식별용 회색조 · 팔레트 및 버튼 기호 유지')
    return {'edits':edits,'zeldat_back_copy':16}


def stage03(resources, output):
    sheets=SubTiles(resources['subtask_us_en.cmp']);rows=[];edits=[]
    for label,k,rect,text,crop in [
        ('친구 모집',1,(32,33,143,47),'친구 모집',(0,32,159,55)),
        ('그룹 만들기',2,(0,128,111,143),'그룹 만들기',(0,128,111,143)),
        ('그룹 참가',2,(0,144,111,159),'그룹 참가',(0,144,111,159)),
        ('그룹 선택',2,(0,184,111,199),'그룹 선택',(0,184,111,199))]:
        before=sheets.image(k,crop)
        edits.append(edit_text(sheets,k,rect,text,background_profile(sheets,k,rect),15,1,13))
        rows.append((label,before,sheets.image(k,crop)))
    resources['subtask_us_en.cmp']=sheets.packed()
    comparison(rows,output/'before_after.png','03 · 멀티플레이 메뉴',scale=3,
               note='실제 롬 그래픽 · 식별용 회색조 · 게임 내 색상은 기존 팔레트 유지')
    return {'edits':edits}


def stage01(resources, output):
    entries = zentries(resources['zeldat_us_en.bin'])
    before = rawentry(entries[9]);pixels = unpack4(before)
    # Extend the already-restored background by three pixels; do not redraw
    # the Korean letters or touch the decorative crescent at the right.
    for y in range(9,13):
        background = pixels[map_index(100,y)]
        for x in range(101,104):
            pixels[map_index(x,y)] = background
    after = pack4(pixels)
    changed = [i for i,(a,b) in enumerate(zip(unpack4(before),pixels)) if a!=b]
    assert changed and all(i//64==29 for i in changed)
    blob = lz.compress_lz11(after)
    assert lz.decompress(blob)==after
    entries[9] = (blob, True)
    resources['zeldat_us_en.bin'] = zpack(entries)
    comparison([('수련장 지도 이름판 · 오른쪽 영문 L 잔여 제거',map_image(before),map_image(after))],
               output/'before_after.png','01 · 수련장 이름판 정리')
    return {'changed_pixels':len(changed),'changed_tiles':[29]}


def build_checkpoint(base_path, original_path, resources, output, details):
    rom = Rom(base_path);original = Rom(original_path)
    base_contents = {name:rom.read(name) for name in rom.names}
    changed_resources = {name:blob for name,blob in resources.items() if blob!=rom.read(name)}
    for name,blob in changed_resources.items():rom.replace(name,blob)
    assert all(e<=rom.data_limit() for s,e in rom.fat)
    fix_digest.fix(rom.data)
    path = output/'KQ9E_ko.nds';path.write_bytes(rom.data)
    check=Rom(path)
    for name,data in base_contents.items():
        assert check.read(name)==changed_resources.get(name,data),name
    again=bytearray(check.data)
    assert fix_digest.fix(again)==(0,False) and again==check.data
    patch=bps.create(bytes(original.data),bytes(check.data))
    assert bps.apply(bytes(original.data),patch)==bytes(check.data)
    (output/'KQ9E_ko_from_original.bps').write_bytes(patch)
    gfx=output/'gfx';gfx.mkdir(exist_ok=True)
    for name,data in resources.items():
        (gfx/name).write_bytes(data)
        p=bps.create(original.read(name),data)
        assert bps.apply(original.read(name),p)==data
        (gfx/(name+'.bps')).write_bytes(p)
    details.update({'base':str(base_path),'rom':str(path),'sha1':hashlib.sha1(check.data).hexdigest(),
                    'changed_resources':list(changed_resources),
                    'verification':['all NitroFS contents match expected','unchanged non-graphics resources',
                                    'digest recomputation idempotent','BPS roundtrip matches ROM']})
    (output/'verification.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(details,ensure_ascii=False,indent=2))


def main():
    sys.stdout.reconfigure(encoding='utf8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',required=True,type=Path)
    p.add_argument('--original',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--stage',required=True,choices=['01','02a','02b','03'])
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    base=Rom(args.base);resources={name:base.read(name) for name in GFX_NAMES}
    details=globals()['stage'+args.stage](resources,args.out)
    build_checkpoint(args.base,args.original,resources,args.out,details)


if __name__=='__main__':main()
