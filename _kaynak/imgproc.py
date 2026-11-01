import os,glob,json,re,unicodedata
from PIL import Image,ImageOps
Image.MAX_IMAGE_PIXELS=None
U="/mnt/user-data/uploads/obruk_icerik/"
OUT="/home/claude/work/site/"
def ascii_name(s):
    tr=str.maketrans("çğıöşüÇĞİÖŞÜ","cgiosuCGIOSU")
    s=s.translate(tr)
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    s=re.sub(r"[^A-Za-z0-9._-]+","-",s)
    return s.lower()
mp={}
def conv(src,dst,maxw,q=78):
    im=Image.open(src); im=ImageOps.exif_transpose(im)
    if im.mode in("P","LA","RGBA"): im=im.convert("RGBA")
    else: im=im.convert("RGB")
    if im.width>maxw: im=im.resize((maxw,int(im.height*maxw/im.width)),Image.LANCZOS)
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    im.save(dst,"WEBP",quality=q,method=5)
    return im.size
for f in sorted(glob.glob(U+"medya/**/*",recursive=True)):
    if os.path.isdir(f) or not f.lower().endswith((".jpg",".jpeg",".png",".gif")): continue
    rel=f[len(U):]
    d,b=os.path.split(rel)
    nb=ascii_name(os.path.splitext(b)[0])
    big="medya/"+"/".join(d.split("/")[1:])+"/"+nb+".webp"
    th="medya/"+"/".join(d.split("/")[1:])+"/"+nb+"-k.webp"
    try:
        sz=conv(f,OUT+big,1400)
        if sz[0]>700: conv(f,OUT+th,640,72); t=th
        else: t=big
        mp[rel]={"src":big,"thumb":t,"w":sz[0],"h":sz[1]}
    except Exception as e: print("ERR",rel,e)
# hero/ek foto
for i,f in enumerate(sorted(glob.glob(U+"ek foto/*"))):
    b=os.path.splitext(os.path.basename(f))[0]
    sz=conv(f,OUT+f"img/saha/{ascii_name(b)}.webp",2000,74)
    conv(f,OUT+f"img/saha/{ascii_name(b)}-k.webp",800,72)
    mp["ek foto/"+os.path.basename(f)]={"src":f"img/saha/{ascii_name(b)}.webp","thumb":f"img/saha/{ascii_name(b)}-k.webp","w":sz[0],"h":sz[1]}
json.dump(mp,open("/home/claude/work/imgmap.json","w"),ensure_ascii=False,indent=0)
print(len(mp))
