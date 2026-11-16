from PIL import Image, ImageDraw, ImageChops, ImageFilter
from pathlib import Path
p=Path.home()/'Downloads/lua_css_layers';out=Path(__file__).resolve().parents[1]/'public/images/lua';out.mkdir(parents=True,exist_ok=True)
ref=Image.open(p/'lua_composite_preview.png').convert('RGBA');head=Image.open(p/'lua_head_open.png').convert('RGBA')
# Common 1536px source canvas; visible pixels always come from the approved composite.
# The replacement body/tail files are different artwork, so their contours are not used.
headmask=head.getchannel('A');body=ref.copy();a=ref.getchannel('A');body.putalpha(ImageChops.subtract(a,headmask))
# Small hidden overlap at the neck, made only from adjacent reference pixels.
under=body.copy()
for dy in range(1,13):
 shifted=Image.new('RGBA',ref.size);shifted.paste(body,(0,-dy));under=Image.alpha_composite(shifted,under)
body=Image.alpha_composite(under,body)
# Distal tail remains behind the body with a 48px opaque overlap at its root.
tailmask=Image.new('L',ref.size);ImageDraw.Draw(tailmask).rectangle((942,680,1535,1295),fill=255)
tail=ref.copy();tail.putalpha(ImageChops.subtract(ImageChops.multiply(a,tailmask),headmask))
cut=Image.new('L',ref.size);ImageDraw.Draw(cut).rectangle((990,680,1535,1295),fill=255)
body.putalpha(ImageChops.subtract(body.getchannel('A'),cut))
# Restore the exact visible body/neck silhouette; overlap exists only underneath the head.
visible=ImageChops.subtract(a,headmask)
body_alpha=body.getchannel('A');keep=ImageChops.lighter(visible,headmask)
body.putalpha(ImageChops.multiply(body_alpha,keep))
# Retain exact reference colors outside the head; hidden neck pixels stay from the overlap.
body.paste(ref,(0,0),ImageChops.subtract(visible,cut))
for name,im in [('composite',ref),('body',body),('tail',tail),('head-open',head),('head-closed',Image.open(p/'lua_head_closed.png'))]:
 im.resize((768,768),Image.Resampling.LANCZOS).save(out/(name+'.webp'),lossless=True,method=6)
# Static expressions are independent, tightly framed and loaded only where rendered.
names={'thinking':'Curious Thinking.png','puppy-eyes':'Puppy Eyes.png','happy':'Happy Wiggle.png','aha':'kai_04_aha_moment_clean.png','celebration':'kai_05_tiny_celebration_clean.png','support':'kai_06_gentle_support_clean.png','wink':'kai_07_playful_wink.png','scholar':'kai_08_little_scholar.png','listening':'kai_09_listening_buddy.png','sleepy':'kai_10_sleepy_dragon.png','wave':'kai_11_shy_wave.png','proud':'kai_12_proud_smile.png','extra':'lua.png'}
for name,file in names.items():
 im=Image.open(Path.home()/'Downloads'/file).convert('RGBA');box=im.getbbox();im=im.crop(box);im.thumbnail((384,384),Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(400,400));canvas.paste(im,((400-im.width)//2,(400-im.height)//2));canvas.save(out/(name+'.webp'),lossless=True,method=6)
