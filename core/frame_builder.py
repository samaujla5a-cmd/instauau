from PIL import Image, ImageDraw, ImageFont
import os, logging
logger = logging.getLogger(__name__)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PALETTES = [
    ((10,0,8),(24,0,15),(255,107,53)), ((4,8,15),(8,15,26),(0,212,255)),
    ((13,10,0),(26,20,0),(255,215,0)), ((6,0,6),(15,0,15),(200,0,255)),
    ((0,10,5),(0,20,9),(0,255,136)), ((16,0,0),(32,0,0),(255,34,34)),
    ((6,6,10),(13,13,24),(255,149,0)),
]

def _font(size):
    try: return ImageFont.truetype(FONT_PATH, size)
    except: return ImageFont.load_default()

def _gradient_bg(w, h, bg, mid):
    strip = Image.new("RGB", (1, h))
    for y in range(h):
        p = y / h
        strip.putpixel((0, y), (max(0,int(bg[0]*(1-p*0.4)+mid[0]*p*0.3)), max(0,int(bg[1]*(1-p*0.4)+mid[1]*p*0.3)), max(0,int(bg[2]*(1-p*0.4)+mid[2]*p*0.3))))
    return strip.resize((w, h))

def _centered(draw, text, y, font, fill, sw=0, sf=(0,0,0), box=None, w=1080):
    if not text: return
    bb = draw.textbbox((0,0), text, font=font); tw = bb[2]-bb[0]; x = (w-tw)//2
    if box: draw.rectangle([x-box, y-box, x+tw+box, y+bb[3]-bb[1]+box], fill=(0,0,0))
    draw.text((x, y), text, fill=fill, font=font, stroke_width=sw, stroke_fill=sf)

def create_rap_frame(title, hook="", palette_idx=0, lyric="", out_path="frame.png", w=1080, h=1920):
    bg, mid, acc = PALETTES[palette_idx % len(PALETTES)]
    img = _gradient_bg(w, h, bg, mid); d = ImageDraw.Draw(img)
    d.rectangle([0,0,w,10], fill=acc); d.rectangle([0,h-10,w,h], fill=acc); d.rectangle([0,0,5,h], fill=acc)
    _centered(d, title[:28], int(h*.07), _font(80), acc, 5, (0,0,0), 22, w)
    if hook: _centered(d, hook[:40], int(h*.22), _font(48), (255,255,255), 2, acc, 12, w)
    _centered(d, "INDIAN HIPHOP", int(h*.07+90), _font(22), acc, 2, (0,0,0), 8, w)
    if lyric: _centered(d, lyric[:45], int(h*.73), _font(38), (255,255,255), 3, acc, 20, w)
    _centered(d, "FOLLOW FOR MORE", int(h*.92), _font(28), (255,255,255), 2, acc, 12, w)
    img.save(out_path, "PNG"); return out_path

def create_model_overlay(quote="", watermark="AI MODEL", w=1080, h=1920, out_path="overlay.png"):
    img = Image.new("RGBA", (w, h), (0,0,0,0)); d = ImageDraw.Draw(img); gold = (255,215,0,230)
    yl = int(h*.76); d.rectangle([int(w*.1), yl, int(w*.9), yl+3], fill=gold)
    if quote:
        safe = quote[:50]; f = _font(48); bb = d.textbbox((0,0), safe, font=f); tw = bb[2]-bb[0]; tx = (w-tw)//2; ty = int(h*.78)
        d.rectangle([tx-14,ty-14,tx+tw+14,ty+60], fill=(0,0,0,140))
        d.text((tx,ty), safe, fill=(255,255,255,255), font=f, stroke_width=3, stroke_fill=(0,0,0,255))
    wf=_font(24); wbb=d.textbbox((0,0),watermark,font=wf); ww=wbb[2]-wbb[0]; wx=w-ww-20; wy=h-50
    d.rectangle([wx-6,wy-6,wx+ww+6,wy+30], fill=(0,0,0,100))
    d.text((wx,wy), watermark, fill=gold, font=wf, stroke_width=2, stroke_fill=(0,0,0,255))
    img.save(out_path, "PNG"); return out_path

def create_brainrot_creature_frame(image_path, creature_name="", w=1080, h=1920, out_path="br_frame.png"):
    img = Image.open(image_path).convert("RGB")
    sc = max(w/img.size[0], h/img.size[1])
    img = img.resize((int(img.size[0]*sc), int(img.size[1]*sc)), Image.LANCZOS)
    iw, ih = img.size; img = img.crop(((iw-w)//2, (ih-h)//2, (iw-w)//2+w, (ih-h)//2+h))
    d = ImageDraw.Draw(img); safe = creature_name.replace("'","")[:25]
    fb=_font(72); bb=d.textbbox((0,0),safe,font=fb); tw=bb[2]-bb[0]; tx=(w-tw)//2
    d.rectangle([tx-16,18,tx+tw+16,98], fill=(0,0,0)); d.text((tx,30), safe, fill=(255,215,0), font=fb, stroke_width=5, stroke_fill=(0,0,0))
    lf=_font(40); lt="HALKU BRAINROT"; lb=d.textbbox((0,0),lt,font=lf); lw=lb[2]-lb[0]; lx=(w-lw)//2
    d.rectangle([lx-10,108,lx+lw+10,158], fill=(255,103,0)); d.text((lx,112), lt, fill=(255,255,255), font=lf, stroke_width=3, stroke_fill=(255,103,0))
    ct="BHAI DEKH LE AUR SHARE KAR"; cf=_font(28); cb=d.textbbox((0,0),ct,font=cf); cw=cb[2]-cb[0]; cx=(w-cw)//2
    d.rectangle([cx-8,h-60,cx+cw+8,h-10], fill=(0,0,0)); d.text((cx,h-55), ct, fill=(255,255,255), font=cf, stroke_width=2, stroke_fill=(0,0,0))
    img.save(out_path, "PNG"); return out_path

def create_placeholder_model(theme="lifestyle", quote="", out_path="ph.jpg", w=1080, h=1920):
    bg_t=(26,5,16); bg_b=(139,26,74); gold=(255,215,0)
    strip = Image.new("RGB", (1, h))
    for y in range(h):
        p=y/h; strip.putpixel((0,y), (int(bg_t[0]+(bg_b[0]-bg_t[0])*p), int(bg_t[1]+(bg_b[1]-bg_t[1])*p), int(bg_t[2]+(bg_b[2]-bg_t[2])*p)))
    img=strip.resize((w,h)); d=ImageDraw.Draw(img)
    d.rectangle([0,0,w,8], fill=gold); d.rectangle([0,h-8,w,h], fill=gold)
    if quote: _centered(d, quote[:40], int(h*.45), _font(68), (255,255,255), 3, (0,0,0), 20, w)
    _centered(d, "AI MODEL", int(h*.55), _font(40), gold, 2, (0,0,0), 10, w)
    img.save(out_path, "JPEG", quality=95); return out_path

def create_brainrot_bg(name="HALKU CREATURE", animal="SHER", cta="BHAI DEKH LE AUR SHARE KAR", w=1080, h=1920, out_path="br_bg.png"):
    bg=(10,10,26); saffron=(255,103,0); green=(19,136,8); gold=(255,215,0)
    img=Image.new("RGB",(w,h),bg); d=ImageDraw.Draw(img)
    d.rectangle([0,0,w,12], fill=saffron); d.rectangle([0,h-12,w,h], fill=green)
    _centered(d, animal[:15], int(h*.30), _font(120), (255,255,255), 5, (0,0,0), 20, w)
    _centered(d, name[:25], int(h*.52), _font(64), gold, 4, (0,0,0), 16, w)
    _centered(d, cta, h-55, _font(28), (255,255,255), 2, (0,0,0), 8, w)
    img.save(out_path, "PNG"); return out_path
