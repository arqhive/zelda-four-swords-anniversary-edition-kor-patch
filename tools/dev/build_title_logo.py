"""Compile the Korean title into both background and runtime OBJ graphics.

Uses the existing 256-color palette, all palette animation data, tilemap,
texture size and archive offsets. Outside the title region, original texture
indices are copied byte-for-byte (including the jewels and credits).
The runtime title also uses localized zeldat entries 12/13, with pat.bin group
181 and zeldat.bin palette 62. Updating the background alone is insufficient.
The input artwork is created with ImageGen; this performs native asset encoding.
"""
from pathlib import Path
import argparse
import hashlib
import struct
import sys

from PIL import Image

from polish_graphics import Rom, lz, comparison, build_checkpoint, GFX_NAMES
from title_sprites import compile_sprite_logo, render_title_sprite

TITLE_ENTRY = 12
PALETTE_ENTRY = 13
MAP_ENTRY = 14
# Native coordinates, right and bottom exclusive. Jewels begin below this.
TITLE_REGION = (28, 14, 227, 132)


def unpack_archive(blob):
    data = lz.decompress(blob)
    count = struct.unpack_from('<I', data)[0] // 4
    offsets = struct.unpack_from('<%dI' % count, data)
    return data, offsets


def palette_rgb(data):
    return [((v & 31)*255//31, ((v>>5)&31)*255//31, ((v>>10)&31)*255//31)
            for v in struct.unpack('<256H', data[:512])]


def texture_image(raw, palette):
    im = Image.new('RGB', (256,192))
    for t in range(768):
        for j in range(64):
            im.putpixel((t%32*8+j%8, t//32*8+j//8),palette[raw[t*64+j]])
    return im


def main():
    sys.stdout.reconfigure(encoding='utf8')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--artwork', type=Path, required=True)
    ap.add_argument('--sprite-artwork', type=Path, required=True,
                    help='Transparent RGBA cutout of the Korean title logo')
    ap.add_argument('--out', type=Path, required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    base=Rom(args.base)
    original_data, offsets=unpack_archive(base.read('subtask.cmp'))
    data=bytearray(original_data)
    tex_off=offsets[TITLE_ENTRY]
    assert data[tex_off:tex_off+4]==b'RGCN'
    assert struct.unpack_from('<I',data,tex_off+0x1c)[0]==4  # 8bpp
    assert struct.unpack_from('<I',data,tex_off+0x28)[0]==256*192
    scr_off=offsets[MAP_ENTRY]
    assert list(struct.unpack_from('<768H',data,scr_off+0x24))==list(range(768))
    palette=palette_rgb(data[offsets[PALETTE_ENTRY]+0x28:])
    start=tex_off+0x30
    before_raw=bytes(data[start:start+256*192])
    before=texture_image(before_raw,palette)
    artwork=Image.open(args.artwork).convert('RGB')
    assert abs(artwork.width/artwork.height-4/3)<0.001
    native=artwork.resize((256,192),Image.Resampling.LANCZOS)
    indexed_palette=Image.new('P',(1,1))
    indexed_palette.putpalette([v for rgb in palette for v in rgb])
    compiled=native.quantize(palette=indexed_palette,dither=Image.Dither.NONE)
    x0,y0,x1,y1=TITLE_REGION
    after_raw=bytearray(before_raw)
    for y in range(y0,y1):
        for x in range(x0,x1):
            off=(y//8*32+x//8)*64+(y%8)*8+x%8
            after_raw[off]=compiled.getpixel((x,y))
    data[start:start+len(after_raw)]=after_raw
    assert data[:start]==original_data[:start]
    assert data[start+len(after_raw):]==original_data[start+len(after_raw):]
    for y in range(192):
        for x in range(256):
            if not (x0<=x<x1 and y0<=y<y1):
                off=(y//8*32+x//8)*64+(y%8)*8+x%8
                assert before_raw[off]==after_raw[off]
    blob=lz.compress_lz11(bytes(data))
    assert lz.decompress(blob)==bytes(data)
    resources={name:base.read(name) for name in GFX_NAMES}
    resources['subtask.cmp']=blob
    sprite_before=render_title_sprite(base)
    resources['zeldat_us_en.bin'], sprite_details=compile_sprite_logo(base,args.sprite_artwork)
    details={'stage':'title_logo_background_and_sprites','title':['젤다의 전설','4개의 검','25주년 에디션'],
             'image_generation':'built-in image_gen; prompt in imagegen_prompt.txt',
             'artwork_sha256':hashlib.sha256(args.artwork.read_bytes()).hexdigest(),
             'region':TITLE_REGION,'original_palette_preserved':True,
             'subtask_other_archive_entries_preserved':True,
             'jewels_and_credits_preserved':True,
             'runtime_test':'Not run; pending user hardware verification.'}
    details.update(sprite_details)
    build_checkpoint(args.base,args.original,resources,args.out,details)
    # Render from the newly built ROM, not from the high-resolution proposal.
    checked=Rom(args.out/'KQ9E_ko.nds')
    checked_data,checked_offsets=unpack_archive(checked.read('subtask.cmp'))
    checked_start=checked_offsets[TITLE_ENTRY]+0x30
    checked_raw=checked_data[checked_start:checked_start+256*192]
    assert checked_raw==bytes(after_raw)
    after=texture_image(checked_raw,palette)
    before.save(args.out/'title_before_256.png')
    after.save(args.out/'title_after_256.png')
    sprite_after=render_title_sprite(checked)
    assert sprite_after.tobytes()==render_title_sprite(checked,13).tobytes()
    sprite_before.save(args.out/'sprite_before_256.png')
    sprite_after.save(args.out/'sprite_after_256.png')
    def preview(im):
        return Image.alpha_composite(Image.new('RGBA',im.size,(70,75,83,255)),im).convert('RGB')
    comparison([('실제 표시용 로고 · 제목과 부제 조각을 원래 배열로 조립',preview(sprite_before),preview(sprite_after))],
               args.out/'before_after.png','타이틀 로고 누락 수정 · 영문 → 한글',scale=2,
               note='완성 롬의 스프라이트 재추출 · 단색 배경은 비교용 · 실기 실행 화면은 아님')


if __name__=='__main__':main()
