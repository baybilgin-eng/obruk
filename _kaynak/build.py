# -*- coding: utf-8 -*-
"""OBRUK statik site üreteci. Çalıştır: python3 build.py"""
import os, re, csv, json, glob, html, shutil, datetime, urllib.parse, posixpath
from collections import Counter, defaultdict
import markdown, yaml
from content import *

SRC = "/mnt/user-data/uploads/obruk_icerik/"
OUT = "/home/claude/work/site/"
IMG = json.load(open("/home/claude/work/imgmap.json", encoding="utf-8"))
PDFOUT = "/home/claude/work/pdfout/"
COVERS = "/home/claude/work/covers/"
TODAY = datetime.date.today().isoformat()
E = html.escape
SITEMAP = []

# ------------------------------------------------------------------ yardımcılar
def tr_lower(s): return s.replace("I", "ı").replace("İ", "i").lower()
def tr_upper_first(w):
    if not w: return w
    c = w[0]; c = "İ" if c == "i" else c.upper()
    return c + w[1:]
KEEP = {"OBRUK", "MESS", "UNESCO", "EAA", "BSU", "NG", "ICS", "UIS", "TMB", "TMF", "ÇEKÜL", "HYPOGEA", "LION", "ATLAS",
        "MAD", "ASPEG", "İTÜMAK", "BÜMAK", "HÜMAK", "AKÜMAK", "ESPS", "AFTES", "SIGEA", "II", "III", "IV", "8B", "2B", "T-SHIRT"}
SMALL = {"ve", "ile", "de", "da", "mi", "mı", "ki", "için", "bir", "and", "of", "the", "in", "on", "at"}
def title_case(t):
    if t != t.upper(): return t
    out = []
    for i, w in enumerate(t.split()):
        core = re.sub(r"[^\wÇĞİÖŞÜçğıöşü-]", "", w)
        if core.upper() in KEEP or re.fullmatch(r"[\d.,:-]+", core or "0"): out.append(w); continue
        lw = tr_lower(w)
        if i > 0 and lw in SMALL: out.append(lw); continue
        # o'mag
        if lw.startswith("o'mag"): out.append(lw); continue
        out.append("-".join(tr_upper_first(p) for p in lw.split("-")))
    return " ".join(out)

def slugify(s):
    s = s.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def read_md(path):
    t = open(path, encoding="utf-8").read()
    meta = {}
    if t.startswith("---"):
        _, fm, t = t.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    return meta, t.strip()

def fmt_date(d, lang="tr"):
    if not d: return ""
    if isinstance(d, str):
        parts = d.split("-")
        y = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else 0; dd = int(parts[2]) if len(parts) > 2 else 0
    else:
        y, m, dd = d.year, d.month, d.day
    mn = UI[lang]["months"][m - 1] if m else ""
    if dd: return f"{dd} {mn} {y}" if lang == "tr" else f"{dd} {mn} {y}"
    return f"{mn} {y}".strip()

def strip_tags(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()
def excerpt(h, n=170):
    t = strip_tags(h)
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t

def rel(frm, to):
    """frm: sayfa yolu ('kayseri/' veya 'en/about/'), to: site kökünden yol ('medya/x.webp' veya 'raporlar/')."""
    base = posixpath.dirname((frm.rstrip("/") + "/index.html").lstrip("/"))
    r = posixpath.relpath(to.rstrip("/") or ".", base or ".")
    if to.endswith("/") and r != ".": r += "/"
    if r == ".": r = "./"
    return urllib.parse.quote(r, safe="/#?=&.-_~%")

def img_of(key):
    k = key.replace("../", "")
    k = urllib.parse.unquote(k)
    if k.startswith("medya/") or k.startswith("ek foto/"):
        return IMG.get(k)
    return None

# ------------------------------------------------------------------ PDF ve kapaklar
PDFS = {}  # kök ad -> dict(path, size, cover)
def prep_pdfs():
    from PIL import Image
    for f in glob.glob(PDFOUT + "pdf/**/*.pdf", recursive=True):
        relp = f[len(PDFOUT):]
        stem = os.path.splitext(os.path.basename(f))[0]
        dst = OUT + relp
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(f): shutil.copy2(f, dst)
        cov = COVERS + relp[:-4] + ".jpg"
        cdst = None
        if os.path.exists(cov):
            cdst = "img/kapak/" + relp[4:-4].lower().replace(" ", "-") + ".webp"
            cdst = cdst.translate(str.maketrans("çğıöşü", "cgiosu"))
            os.makedirs(os.path.dirname(OUT + cdst), exist_ok=True)
            im = Image.open(cov).convert("RGB"); im.thumbnail((420, 600)); im.save(OUT + cdst, "WEBP", quality=74)
        PDFS[stem] = {"path": relp, "size": os.path.getsize(f), "cover": cdst}
def pdf(stem): return PDFS.get(stem)
def mb(n): return f"{n/1e6:.1f} MB".replace(".", ",")

# ------------------------------------------------------------------ markdown dönüştürme
POSTMAP = {}   # md göreli yol -> yeni slug
def md_to_html(text, page_path):
    text = text.replace("\\*", "*")
    text = re.sub(r"php print theme\([^\n]*\?>", "", text)
    h = markdown.markdown(text, extensions=["tables", "sane_lists"])
    def fix_src(m):
        attr, url = m.group(1), m.group(2)
        u = urllib.parse.unquote(url)
        u2 = re.sub(r"^(\.\./)+", "", u)
        im = img_of(u2)
        if im:
            key = "src" if attr == "src" else "src"
            return f'{attr}="{rel(page_path, im["src"])}"'
        if u2.startswith("pdf/"):
            stem = os.path.splitext(os.path.basename(u2))[0]
            p = pdf(stem)
            if p: return f'{attr}="{rel(page_path, p["path"])}"'
        if u2.startswith(("yazilar/", "sayfalar/", "drupal_arsivi/")):
            s = POSTMAP.get(u2)
            if s: return f'{attr}="{rel(page_path, s)}"'
        if url.startswith(("/gallery3", "/tr/", "/node", "/haritalar", "/yayin", "/sites", "/20", "/obruk-sayi")):
            return f'{attr}="#" data-dead="1"'
        return m.group(0)
    h = re.sub(r'(src|href)="([^"]+)"', fix_src, h)
    # ölü linkleri metne çevir
    h = re.sub(r'<img[^>]*data-dead="1"[^>]*>', "", h)
    h = re.sub(r'<a href="[^"]+\.(?:mp4|mov)">(.*?)</a>', r"\1", h, flags=re.S | re.I)
    h = re.sub(r'<a href="#" data-dead="1">(.*?)</a>', r"\1", h, flags=re.S)
    h = re.sub(r"<p>\s*</p>", "", h)
    h = re.sub(r"<img ", '<img loading="lazy" decoding="async" ', h)
    h = re.sub(r'<img ([^>]*?)alt=""', r'<img \1alt=""', h)
    h = h.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return h

# ------------------------------------------------------------------ şablon
OMAG = '<img class="logo-omag" src="{R}img/logo-omag.svg" alt="" width="78" height="30">'
LOGO_FULL = '<img class="logo-full" src="{R}img/logo-full.svg" alt="o\'mag OBRUK Mağara Araştırma Grubu" width="210" height="151">'
LOGO = '<img class="logo-omag" src="{R}img/logo-omag-koyu.svg" alt="" width="78" height="30">'

def nav_html(lang, page_path, current):
    u = UI[lang]; pre = "en/" if lang == "en" else ""
    items = []
    for slug, label in u["nav"]:
        if slug == "arsiv":
            sub = "".join(f'<li><a href="{rel(page_path, s + "/")}">{E(l)}</a></li>' for s, l in u["archive_menu"])
            active = ' aria-current="page"' if current in [s for s, _ in u["archive_menu"]] else ""
            items.append(f'<li class="has-sub"><button class="sub-toggle" aria-expanded="false"{active}>{E(label)}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></button><ul class="sub">{sub}</ul></li>')
        else:
            a = ' aria-current="page"' if current == slug else ""
            items.append(f'<li><a href="{rel(page_path, pre + slug + "/")}"{a}>{E(label)}</a></li>')
    return "".join(items)

def page(lang, path, title, body, desc="", current="", alt=None, og_img=None, jsonld=None, body_class="", extra_head=""):
    u = UI[lang]
    full_title = f"{title} · {SITE['name_' + lang]}" if title else f"{SITE['name_' + lang]} — " + ("Yerin altını belgeliyoruz" if lang == "tr" else "Documenting the underground")
    canon = SITE["url"] + "/" + path
    desc = desc or ("OBRUK Mağara Araştırma Grubu: Türkiye'nin mağaralarını ve yeraltı yapılarını keşfeden, haritalayan ve yayımlayan gönüllü mağaracılar." if lang == "tr" else "OBRUK Cave Research Group: volunteer cavers exploring, mapping and publishing the caves and underground structures of Turkey.")
    og = SITE["url"] + "/" + (og_img or "img/og.jpg")
    hreflang = ""
    sw_href = rel(path, "en/") if lang == "tr" else rel(path, "")
    if alt is not None:
        tr_p, en_p = (path, alt) if lang == "tr" else (alt, path)
        hreflang = f'<link rel="alternate" hreflang="tr" href="{SITE["url"]}/{tr_p}"><link rel="alternate" hreflang="en" href="{SITE["url"]}/{en_p}"><link rel="alternate" hreflang="x-default" href="{SITE["url"]}/{tr_p}">'
        sw_href = rel(path, alt)
    ld = ""
    if jsonld:
        ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'
    css = rel(path, "assets/site.css"); js = rel(path, "assets/site.js")
    home = rel(path, "en/" if lang == "en" else "")
    sw_code, sw_label = u["switch"]
    foot_links = [("hakkimizda", "Hakkımızda"), ("arastirmalar", "Araştırmalar"), ("raporlar", "Raporlar"), ("yayinlar", "Yayınlar"), ("katil", "Bize katılın"), ("kurumsal-kimlik", "Logo ve kurumsal kimlik"), ("iletisim", "İletişim")] if lang == "tr" else \
                 [("en/about", "About"), ("en/research", "Research"), ("en/reports", "Reports"), ("en/publications", "Publications"), ("en/inventory", "Cave inventory"), ("en/brand", "Logo and brand"), ("en/contact", "Contact")]
    foot_links2 = [("magara-envanteri", "Mağara envanteri"), ("saha-gunlugu", "Saha günlüğü"), ("bilgi-bankasi", "Bilgi bankası"), ("koruma", "Koruma ve etik"), ("magaracilik-sinavi", "Mağaracılık sınavı"), ("en", "English")] if lang == "tr" else \
                  [("", "Türkçe site"), ("saha-gunlugu", "Field journal (TR)"), ("magaracilik-sinavi", "Caving quiz (TR)")]
    fl = "".join(f'<li><a href="{rel(path, s + "/" if s else "")}">{E(l)}</a></li>' for s, l in foot_links)
    fl2 = "".join(f'<li><a href="{rel(path, s + "/" if s else "")}">{E(l)}</a></li>' for s, l in foot_links2)
    year = datetime.date.today().year
    SITEMAP.append(path)
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full_title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}">
{hreflang}
<meta property="og:type" content="{'article' if jsonld and jsonld.get('@type')=='Article' else 'website'}">
<meta property="og:site_name" content="{E(SITE['name_' + lang])}">
<meta property="og:title" content="{E(title or SITE['name_' + lang])}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og}">
<meta property="og:locale" content="{u['locale']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1E1B17">
<link rel="icon" href="{rel(path, 'favicon.svg')}" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
{extra_head}{ld}
</head>
<body class="{body_class}">
<a class="skip" href="#main">{u['skip']}</a>
<header class="site-header">
  <div class="wrap header-in">
    <a class="brand" href="{home}" aria-label="{E(SITE['name_' + lang])}">{OMAG.replace("{R}", (rel(path, "").rstrip("/") + "/") if path else "")}<span class="brand-sep" aria-hidden="true"></span><span class="brand-text"><span class="brand-name">OBRUK</span><span class="brand-tag">{E(u['tagline'])}</span></span></a>
    <button class="menu-toggle" aria-expanded="false" aria-controls="nav"><span></span><span></span><span></span><span class="sr">Menü</span></button>
    <nav id="nav" class="nav" aria-label="Ana menü"><ul>{nav_html(lang, path, current)}<li class="lang"><a href="{sw_href}" hreflang="{sw_code.lower()}" lang="{sw_code.lower()}" title="{sw_label}">{sw_code}</a></li></ul></nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap foot-grid">
    <div class="foot-about">
      <a class="brand-foot" href="{home}">{LOGO_FULL.replace("{R}", (rel(path, "").rstrip("/") + "/") if path else "")}</a>
      <p>{E(u['footer_note'])}</p>
      <p><a class="mail" data-u="ayamac" data-d="gmail.com" href="mailto:ayamac@gmail.com">ayamac@gmail.com</a></p>
    </div>
    <div><h2 class="foot-h">{'Kurum' if lang=='tr' else 'Group'}</h2><ul>{fl}</ul></div>
    <div><h2 class="foot-h">{'Arşiv' if lang=='tr' else 'Archive'}</h2><ul>{fl2}</ul></div>
  </div>
  <div class="wrap foot-bottom"><span>© 2008–{year} OBRUK Mağara Araştırma Grubu</span><span><a href="mailto:ayamac@gmail.com">ayamac@gmail.com</a></span></div>
</footer>
<script src="{js}" defer></script>
</body>
</html>'''

def write(path, html_str):
    p = OUT + path + ("index.html" if path.endswith("/") or path == "" else "")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(html_str)

BANNERS = json.load(open("/home/claude/work/banners.json"))
def banner_attr(path):
    lst = [rel(path, b) for b in BANNERS]
    first = lst[sum(map(ord, path)) % len(lst)]
    return first, E(json.dumps(lst))

def page_head(kicker, title, lead="", img=None, path=""):
    bg = ""
    if img:
        first, lst = banner_attr(path)
        bg = f' style="--bg:url(\'{first}\')" data-banners="{lst}"'
    cls = "page-head has-img" if bg else "page-head"
    return f'<section class="{cls}"{bg}><div class="wrap"><p class="kicker">{E(kicker)}</p><h1>{E(title)}</h1>{f"<p class=\"lead\">{lead}</p>" if lead else ""}</div></section>'

# ------------------------------------------------------------------ veri yükleme
def load_posts():
    posts = []
    for f in sorted(glob.glob(SRC + "yazilar/*.md")):
        meta, body = read_md(f)
        posts.append({"file": f[len(SRC):], "meta": meta, "body": body, "kind": "haber"})
    for f in sorted(glob.glob(SRC + "drupal_arsivi/blog/*.md")):
        meta, body = read_md(f)
        if str(meta.get("durum", "")).startswith("yayinda-degil"): continue
        posts.append({"file": f[len(SRC):], "meta": meta, "body": body, "kind": "kose"})
    for p in posts:
        m = p["meta"]
        p["slug"] = m.get("slug") or slugify(os.path.basename(p["file"])[11:-3])
        p["date"] = str(m.get("tarih", os.path.basename(p["file"])[:10]))
        t = m.get("baslik") or os.path.basename(p["file"])[11:-3]
        p["title"] = title_case(str(t).strip())
        p["year"] = p["date"][:4]
        body = re.sub(r"^#\s+.*\n", "", p["body"], count=1)
        p["body"] = body
        cov = m.get("kapak_gorseli")
        if not cov:
            mm = re.search(r"!\[[^\]]*\]\((\.\./medya/[^)\s]+)\)", body)
            cov = mm.group(1) if mm else None
        p["cover"] = img_of(cov) if cov else None
        POSTMAP[p["file"]] = p["slug"] + "/"
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts

def load_pages():
    pages = {}
    for f in glob.glob(SRC + "sayfalar/**/*.md", recursive=True):
        if "/taslaklar/" in f and not any(k in f for k in ("egitim-programlari", "calisma-bolgelerimiz")): continue
        meta, body = read_md(f)
        slug = meta.get("slug") or os.path.basename(f)[:-3]
        relp = f[len(SRC):]
        pages[relp] = {"file": relp, "meta": meta, "body": re.sub(r"^#\s+.*\n", "", body, count=1),
                       "title": title_case(str(meta.get("baslik", slug)).strip().rstrip(".")), "slug": slug}
        POSTMAP[relp] = slug + "/"
    return pages

def load_caves():
    rows = list(csv.DictReader(open(SRC + "drupal_arsivi/veri/magara_haritalari.csv", encoding="utf-8-sig")))
    for r in rows:
        if r["il"] == "Bartin": r["il"] = "Bartın"
        names = [MEMBER_NORMALIZE.get(n.strip(), n.strip()) for n in re.split(r",| ve ", r["cizen"])]
        r["cizenler"] = [n for n in names if n not in MEMBER_EXCLUDE]
    return rows

# ------------------------------------------------------------------ bileşenler
def card_post(p, path, lang="tr"):
    im = p["cover"]
    pic = f'<img src="{rel(path, im["thumb"])}" alt="" loading="lazy" decoding="async">' if im else f'<div class="ph">{LOGO.replace("{R}", (rel(path, "").rstrip("/") + "/") if path else "")}</div>'
    tag = "Köşe yazısı" if p["kind"] == "kose" else "Saha günlüğü"
    return f'''<article class="card post-card"><a href="{rel(path, p['slug'] + '/')}"><div class="card-img">{pic}</div><div class="card-body"><p class="meta"><span>{fmt_date(p['date'], lang)}</span><span class="dot">·</span><span>{tag}</span></p><h3>{E(p['title'])}</h3><p>{E(excerpt(md_to_html(p['body'], path), 130))}</p></div></a></article>'''

def doc_card(stem, title, sub, path, lang="tr", big=False):
    p = pdf(stem)
    if not p: return ""
    cov = f'<img src="{rel(path, p["cover"])}" alt="{E(title)} kapak" loading="lazy" decoding="async">' if p["cover"] else '<div class="ph"></div>'
    return f'''<a class="doc{' doc-big' if big else ''}" href="{rel(path, p['path'])}" target="_blank" rel="noopener"><div class="doc-cover">{cov}</div><div class="doc-body"><h3>{E(title)}</h3><p class="meta">{E(sub)}</p><span class="doc-dl"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8m0 0l-3-3m3 3l3-3M3 13h10" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>PDF · {mb(p['size'])}</span></div></a>'''

def project_card(pr, path, lang="tr", big=False):
    t = pr["title"] if lang == "tr" else pr["title_en"]
    s = pr["sum"] if lang == "tr" else pr["sum_en"]
    y = pr["years"] if lang == "tr" else pr["years_en"]
    st = {"active": ("Devam ediyor", "Ongoing"), "long": ("Uzun soluklu", "Long-term"), "done": ("Tamamlandı", "Completed")}[pr["status"]]
    stl = st[0] if lang == "tr" else st[1]
    im = IMG.get(pr["img"]) if pr["img"] else None
    pic = f'<img src="{rel(path, im["thumb"])}" alt="" loading="lazy" decoding="async">' if im else f'<div class="ph">{LOGO.replace("{R}", (rel(path, "").rstrip("/") + "/") if path else "")}</div>'
    partners = pr["partners"] if lang == "tr" else pr["partners_en"]
    reps = ""
    if pr["reports"]:
        links = []
        for r in pr["reports"]:
            pp = pdf(r)
            if pp:
                name = next((x[1] if lang == "tr" else x[2] for x in REPORTS if x[0] == r), r)
                links.append(f'<a href="{rel(path, pp["path"])}" target="_blank" rel="noopener">{E(name)}</a>')
        if links: reps = f'<p class="proj-reps"><strong>{"Raporlar" if lang=="tr" else "Reports"}:</strong> ' + " · ".join(links) + "</p>"
    return f'''<article class="proj{' proj-big' if big else ''}" id="{pr['slug']}"><div class="proj-img">{pic}<span class="badge badge-{pr['status']}">{stl}</span></div><div class="proj-body"><p class="meta">{E(y)} · {E(pr['il'])}</p><h3>{E(t)}</h3><p>{E(s)}</p>{f'<p class="partners">{E(partners)}</p>' if partners else ''}{reps}</div></article>'''

# ------------------------------------------------------------------ sayfalar
def build_home(lang, posts, caves, members):
    path = "en/" if lang == "en" else ""
    hero = IMG["ek foto/20240905_094908.jpg"]
    n_il = len({c["il"] for c in caves} | {p["il"] for p in PROJECTS})
    stats = [("2008", "Kuruluş yılı" if lang == "tr" else "Founded"),
             (str(len(caves)), "Haritalı mağara kaydı" if lang == "tr" else "Mapped cave records"),
             (str(len(REPORTS)), "Yayımlanmış rapor" if lang == "tr" else "Published reports"),
             (str(len(POSTERS)), "Bildiri ve poster" if lang == "tr" else "Papers and posters"),
             (str(n_il), "İlde çalışma" if lang == "tr" else "Provinces surveyed")]
    st = "".join(f'<div class="stat"><span class="stat-n">{n}</span><span class="stat-l">{E(l)}</span></div>' for n, l in stats)
    if lang == "tr":
        h1 = "Yerin altını ölçüyor, çiziyor, kayda geçiriyoruz"
        lead = "OBRUK, Anadolu'nun mağaralarını ve tarihî yeraltı yapılarını araştıran gönüllü mağaracıların ortak çatısı. 2008'den bu yana keşfediyor, haritalıyor ve yayımlıyoruz."
        c1, c2 = ("Araştırmalarımız", "arastirmalar/"), ("Obruk'u tanıyın", "hakkimizda/")
    else:
        h1 = "We survey, map and record the underground"
        lead = "OBRUK is the shared home of volunteer cavers researching Anatolia's caves and historic underground structures. Exploring, mapping and publishing since 2008."
        c1, c2 = ("Our research", "en/research/"), ("About OBRUK", "en/about/")
    what = [
        ("Keşif ve haritalama", "Exploration and survey", "Doğal mağaraları keşfediyor, ölçüyor ve uluslararası standartlarda haritalıyoruz. Keş Dağı Düdeni'nden İnsuyu'na kadar.", "We explore, survey and map natural caves to international standards — from Keş Mountain Sinkhole to Insuyu.",
         '<path d="M4 20l5-9 4 6 3-4 4 7z M14 6a2 2 0 1 0 0.01 0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'),
        ("Yeraltı yapıları envanteri", "Underground heritage inventories", "Yeraltı şehirleri, kaya yerleşimleri, su tünelleri ve güvercinlikleri belediyeler ve müzelerle birlikte belgeliyoruz.", "With municipalities and museums we document underground cities, rock-cut settlements, water tunnels and dovecotes.",
         '<path d="M3 20h18M5 20V10l7-5 7 5v10M9 20v-5h6v5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'),
        ("Yayın ve paylaşım", "Publishing and sharing", "OBRUK Dergisi, raporlar, kongre bildirileri ve basın yazılarıyla bulguları kalıcı hale getiriyoruz.", "Through OBRUK Magazine, reports, congress papers and the press, we make our findings permanent.",
         '<path d="M4 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4zM20 5h-6M20 5v13h-6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'),
    ]
    whtml = "".join(f'<div class="what"><svg viewBox="0 0 24 24" aria-hidden="true">{ic}</svg><h3>{E(a if lang=="tr" else b)}</h3><p>{E(c if lang=="tr" else d)}</p></div>' for a, b, c, d, ic in what)
    feat = "".join(project_card(p, path, lang) for p in PROJECTS[:4])
    gal_keys = ["ek foto/20241013_122511.jpg", "ek foto/20250218_151807.jpg", "ek foto/20250612_134740.jpg", "ek foto/20250722_123358.jpg", "ek foto/20250612_142712.jpg"]
    gal = "".join(f'<figure class="m{i}"><img src="{rel(path, IMG[k]["thumb"] if i else IMG[k]["src"])}" alt="{"Saha çalışmasından" if lang=="tr" else "From the field"}" loading="lazy" decoding="async"></figure>' for i, k in enumerate(gal_keys))
    reps = "".join(doc_card(r[0], r[1] if lang == "tr" else r[2], fmt_date(r[3], lang) + " · " + r[4], path, lang) for r in REPORTS[:6])
    latest = "".join(card_post(p, path, lang) for p in posts[:3]) if lang == "tr" else ""
    reports_link = rel(path, "raporlar/" if lang == "tr" else "en/reports/")
    if lang == "tr":
        quote = "Kapısına kadar araç gitmeyen mağaralarla ilgilenmeyerek, gelecek nesillere araştırılacak mağara bırakma özverisinde bulunabilecek etik anlayışa sahip…"
        join_t, join_p, join_b = "Gelecek kuşak mağaracılara güçlü bir OBRUK", "OBRUK'un birikimi; ölçen, çizen, yazan ve paylaşan her yeni mağaracıyla büyüyor. Saha çalışmalarına katılmak, haritalara ve dergiye katkı vermek ister misiniz?", ("Bize katılın", "katil/")
    else:
        quote = None
        join_t, join_p, join_b = "A strong OBRUK for the next generation of cavers", "OBRUK grows with every new caver who surveys, draws, writes and shares. Would you like to join our fieldwork or contribute to the maps and the magazine?", ("Get in touch", "en/contact/")
    posts_sec = f'''<section class="sec"><div class="wrap"><div class="sec-head"><h2>Saha günlüğünden</h2><a class="more" href="{rel(path, 'saha-gunlugu/')}">{UI[lang]['all_posts']} →</a></div><div class="grid g3">{latest}</div></div></section>''' if lang == "tr" else ""
    quote_html = f'<blockquote class="founder-quote"><p>“{E(quote)}”</p><cite>OBRUK, <a href="{rel(path, "hakkimizda/")}#kendi-kalemimizden">Hakkımızda</a></cite></blockquote>' if quote else ""
    body = f'''
<section class="hero"><img class="hero-img" src="{banner_attr(path)[0]}" data-banners="{banner_attr(path)[1]}" alt="" fetchpriority="high"><div class="hero-shade"></div>
<div class="wrap hero-in"><p class="kicker">{'Mağara Araştırma Grubu · 2008’den beri' if lang=='tr' else 'Cave Research Group · since 2008'}</p><h1>{E(h1)}</h1><p class="lead">{E(lead)}</p><div class="cta"><a class="btn btn-primary" href="{rel(path, c1[1])}">{E(c1[0])}</a><a class="btn btn-ghost" href="{rel(path, c2[1])}">{E(c2[0])}</a></div></div></section>
<section class="stats"><div class="wrap stats-in">{st}</div></section>
<section class="sec"><div class="wrap"><div class="sec-head"><h2>{'Ne yapıyoruz?' if lang=='tr' else 'What we do'}</h2></div><div class="grid g3 whats">{whtml}</div></div></section>
<section class="sec sec-alt"><div class="wrap"><div class="sec-head"><h2>{'Öne çıkan projeler' if lang=='tr' else 'Featured projects'}</h2><a class="more" href="{rel(path, 'arastirmalar/' if lang=='tr' else 'en/research/')}">{'Tüm araştırmalar' if lang=='tr' else 'All research'} →</a></div><div class="grid g2 projs">{feat}</div></div></section>
<section class="mosaic" aria-label="{'Sahadan fotoğraflar' if lang=='tr' else 'Field photographs'}"><div class="wrap"><div class="mosaic-grid">{gal}</div></div></section>
<section class="sec"><div class="wrap"><div class="sec-head"><h2>{'Raporlar' if lang=='tr' else 'Reports'}</h2><a class="more" href="{reports_link}">{'Tüm raporlar' if lang=='tr' else 'All reports'} →</a></div><div class="docs">{reps}</div></div></section>
{posts_sec}
<section class="join"><div class="wrap join-in">{quote_html}<div class="join-box"><h2>{E(join_t)}</h2><p>{E(join_p)}</p><a class="btn btn-dark" href="{rel(path, join_b[1])}">{E(join_b[0])}</a></div></div></section>'''
    jsonld = {"@context": "https://schema.org", "@type": "Organization", "name": SITE["name_" + lang], "alternateName": ["OBRUK", "o'mag", "Obruk Mağara Araştırma Grubu"],
              "url": SITE["url"] + "/" + path, "logo": SITE["url"] + "/img/logo.png", "email": SITE["email"], "foundingDate": "2008", "foundingLocation": "İstanbul",
              "nonprofitStatus": "Nonprofit",
              "description": lead, "knowsAbout": ["Speleology", "Cave survey", "Underground cities", "Cappadocia", "Cave conservation"]}
    write(path, page(lang, path, "", body, current="", alt=("en/" if lang == "tr" else ""), og_img="img/og.jpg", jsonld=jsonld, body_class="home"))

def build_about(lang, pages):
    path = "hakkimizda/" if lang == "tr" else "en/about/"
    alt = "en/about/" if lang == "tr" else "hakkimizda/"
    tl = "".join(f'<li><span class="tl-y">{E(y)}</span><p>{E(a if lang=="tr" else b)}</p></li>' for y, a, b in TIMELINE)
    pr = "".join(f'<div class="principle"><h3>{E(a if lang=="tr" else b)}</h3><p>{E(c if lang=="tr" else d)}</p></div>' for a, b, c, d in PRINCIPLES)
    partners = ["Kayseri Büyükşehir Belediyesi", "Gaziantep Büyükşehir Belediyesi", "Ürgüp Belediyesi", "ÇEKÜL Vakfı", "Doğa Koruma ve Milli Parklar Genel Müdürlüğü", "Nevşehir Müze Müdürlüğü", "Aksaray Müze Müdürlüğü", "İTÜMAK · BÜMAK · ASPEG · HÜMAK · AKÜMAK"]
    if lang == "en":
        partners = ["Kayseri Metropolitan Municipality", "Gaziantep Metropolitan Municipality", "Municipality of Ürgüp", "ÇEKÜL Foundation", "General Directorate of Nature Conservation and National Parks", "Nevşehir Museum Directorate", "Aksaray Museum Directorate", "University caving clubs: İTÜMAK · BÜMAK · ASPEG · HÜMAK · AKÜMAK"]
    pl = "".join(f"<li>{E(p)}</li>" for p in partners)
    founder_html = ""
    if lang == "tr":
        h = pages["sayfalar/hakkimizda.md"]
        founder_html = f'<section class="sec sec-alt" id="kendi-kalemimizden"><div class="wrap narrow"><p class="kicker">Kendi kalemimizden</p><h2>“Bu küçük grubun şaşkın üyeleri…”</h2><div class="prose founder">{md_to_html(h["body"], path)}</div></div></section>'
    else:
        founder_html = ''
    body = page_head("OBRUK" if lang == "tr" else "OBRUK", "Hakkımızda" if lang == "tr" else "About us",
                     "2008'den bu yana Anadolu'nun yeraltını belgeleyen, kâr amacı gütmeyen gönüllü mağaracılar topluluğu." if lang == "tr" else "A volunteer, non-profit community of cavers documenting Anatolia's underground since 2008.",
                     "ek foto/20241013_122511.jpg", path) + f'''
<section class="sec"><div class="wrap two-col"><div class="prose">{ABOUT_TR if lang=='tr' else ABOUT_EN}</div>
<aside class="facts"><h2>{'Kısaca OBRUK' if lang=='tr' else 'OBRUK at a glance'}</h2><dl>
<dt>{'Kuruluş' if lang=='tr' else 'Founded'}</dt><dd>{'2008, İstanbul' if lang=='tr' else '2008, Istanbul'}</dd>
<dt>{'Yapı' if lang=='tr' else 'Status'}</dt><dd>{'Kâr amacı gütmeyen gönüllü sivil oluşum' if lang=='tr' else 'Volunteer, non-profit civic group'}</dd>
<dt>{'Odak' if lang=='tr' else 'Focus'}</dt><dd>{'Mağara keşfi ve haritalama, yeraltı yapıları envanteri, yayın' if lang=='tr' else 'Cave exploration and survey, underground heritage inventories, publishing'}</dd>
<dt>{'Yayın' if lang=='tr' else 'Publication'}</dt><dd>{'OBRUK Dergisi (7 sayı)' if lang=='tr' else 'OBRUK Magazine (7 issues)'}</dd>
<dt>{'İletişim' if lang=='tr' else 'Contact'}</dt><dd><a href="mailto:ayamac@gmail.com">ayamac@gmail.com</a></dd>
<dt>Logo</dt><dd><a href="{rel(path, 'kurumsal-kimlik/' if lang=='tr' else 'en/brand/')}">{'Yüksek çözünürlüklü indir' if lang=='tr' else 'Download in high resolution'}</a></dd></dl></aside></div></section>
<section class="sec sec-alt"><div class="wrap"><div class="sec-head"><h2>{'İlkelerimiz' if lang=='tr' else 'Our principles'}</h2></div><div class="grid g4 principles">{pr}</div></div></section>
<section class="sec"><div class="wrap narrow"><div class="sec-head"><h2>{'Kilometre taşları' if lang=='tr' else 'Milestones'}</h2></div><ol class="timeline">{tl}</ol></div></section>
<section class="sec sec-alt"><div class="wrap"><div class="sec-head"><h2>{'İş birliği yaptığımız kurumlar' if lang=='tr' else 'Partners'}</h2></div><ul class="partners-list">{pl}</ul></div></section>
{founder_html}'''
    write(path, page(lang, path, "Hakkımızda" if lang == "tr" else "About us", body,
                     desc=("OBRUK Mağara Araştırma Grubu kimdir? Kuruluş, ilkeler, kilometre taşları ve iş birlikleri." if lang == "tr" else "Who is the OBRUK Cave Research Group? History, principles, milestones and partners."),
                     current="hakkimizda" if lang == "tr" else "about", alt=alt))

def member_stats(caves, posts):
    m = defaultdict(lambda: {"maps": 0, "il": Counter(), "years": set(), "mentions": 0})
    for c in caves:
        for n in c["cizenler"]:
            m[n]["maps"] += 1; m[n]["il"][c["il"]] += 1
            if c["olcum_ay_yil"]: m[n]["years"].add(c["olcum_ay_yil"][:4])
    for n in EXTRA_MEMBERS: m[n]
    alltext = " ".join(p["body"] for p in posts)
    for n in m:
        m[n]["mentions"] = sum(1 for p in posts if n in p["body"])
    return m

def build_members(lang, caves, posts):
    path = "magaracilar/" if lang == "tr" else "en/cavers/"
    alt = "en/cavers/" if lang == "tr" else "magaracilar/"
    ms = member_stats(caves, posts)
    order = sorted(ms.items(), key=lambda kv: (kv[0] != "Ali Yamaç", -kv[1]["maps"], kv[0]))
    cards = []
    for n, s in order:
        ini = "".join(w[0] for w in n.split()[:2] if w)
        ils = ", ".join(i for i, _ in s["il"].most_common(4))
        yrs = sorted(s["years"]); yr = f"{yrs[0]}–{yrs[-1]}" if len(yrs) > 1 else (yrs[0] if yrs else "")
        role = ("Kurucu" if lang == "tr" else "Founder") if n == "Ali Yamaç" else ""
        cards.append(f'''<article class="member{' member-founder' if role else ''}"><div class="avatar" aria-hidden="true">{E(ini)}</div><div><h3>{E(n)}</h3>{f'<p class="role">{role}</p>' if role else ''}<p class="meta">{(str(s['maps']) + (' harita' if lang=='tr' else ' maps') + ((' · ' + yr) if yr else '')) if s['maps'] else ((str(s['mentions']) + (' saha yazısında adı geçiyor' if lang=='tr' else ' field reports')) if s['mentions'] else ('Ekip üyesi' if lang=='tr' else 'Team member'))}</p><p class="ils">{E(ils)}</p></div></article>''')
    intro = ("OBRUK'un gücü, sahada ip çeken, ölçen, çizen ve yazan mağaracılarıdır. Mağara haritası çizen üyelerin kartlarında envanterdeki harita sayısı, ölçüm yılları ve en çok çalıştığı iller yer alır."
             if lang == "tr" else
             "OBRUK's strength lies in the cavers who rig, survey, draw and write. For members credited as surveyors, each card shows the number of maps in the inventory, survey years and main provinces.")
    note = ("Liste düzenli olarak güncellenir. Adınızın eklenmesini, düzeltilmesini ya da kaldırılmasını isterseniz bize yazın." if lang == "tr"
            else "This list is updated regularly. Write to us if you would like your name added, corrected or removed.")
    body = page_head("OBRUK", "Mağaracılar" if lang == "tr" else "Cavers", E(intro), "ek foto/20250612_132837.jpg", path) + f'''
<section class="sec"><div class="wrap"><div class="members">{''.join(cards)}</div><p class="note">{E(note)} <a href="{rel(path, 'iletisim/' if lang=='tr' else 'en/contact/')}">{'İletişim' if lang=='tr' else 'Contact'} →</a></p></div></section>'''
    write(path, page(lang, path, "Mağaracılar" if lang == "tr" else "Cavers", body,
                     desc=("OBRUK Mağara Araştırma Grubu üyesi mağaracılar ve çizdikleri mağara haritaları." if lang == "tr" else "Members of the OBRUK Cave Research Group and the cave maps they drew."),
                     current="magaracilar" if lang == "tr" else "cavers", alt=alt))

def build_research(lang, posts, caves):
    path = "arastirmalar/" if lang == "tr" else "en/research/"
    alt = "en/research/" if lang == "tr" else "arastirmalar/"
    cards = "".join(project_card(p, path, lang, big=(i == 0)) for i, p in enumerate(PROJECTS))
    # yıllara göre saha yazısı sayısı
    yc = Counter(p["year"] for p in posts if p["kind"] == "haber")
    years = list(range(2010, 2022)); mx = max(yc.values())
    bars = "".join(f'<div class="bar" style="--h:{yc.get(str(y),0)/mx:.3f}" title="{y}: {yc.get(str(y),0)}"><span class="bar-n">{yc.get(str(y),0)}</span><span class="bar-y">{str(y)[2:]}</span></div>' for y in years)
    # harita verisi
    ilc = Counter(c["il"] for c in caves)
    pts = {}
    for il, n in ilc.items():
        if il in IL: pts[il] = {"ll": IL[il], "caves": n, "proj": []}
    for p in PROJECTS:
        il = p["il"]
        if il in IL:
            pts.setdefault(il, {"ll": IL[il], "caves": 0, "proj": []})["proj"].append(p["title"] if lang == "tr" else p["title_en"])
    mapdata = json.dumps([{"il": k, **v} for k, v in pts.items()], ensure_ascii=False)
    lst = ""
    if lang == "tr":
        recent = [p for p in posts if p["kind"] == "haber"][:9]
        lst = f'<section class="sec sec-alt"><div class="wrap"><div class="sec-head"><h2>Son saha çalışmaları</h2><a class="more" href="{rel(path, "saha-gunlugu/")}">Saha günlüğü →</a></div><div class="grid g3">{"".join(card_post(p, path) for p in recent)}</div></div></section>'
    head = f'<link rel="stylesheet" href="{rel(path, "assets/leaflet/leaflet.css")}">'
    body = page_head("OBRUK", "Araştırmalar" if lang == "tr" else "Research",
                     ("2008'den bu yana yürüttüğümüz mağara keşifleri, yeraltı yapıları envanterleri ve ortak projeler." if lang == "tr" else "Cave explorations, underground heritage inventories and joint projects since 2009."),
                     "ek foto/20240905_094908.jpg", path) + f'''
<section class="sec"><div class="wrap"><div class="grid g2 projs projs-all">{cards}</div></div></section>
<section class="sec sec-alt"><div class="wrap two-col map-row"><div><h2>{'Çalıştığımız iller' if lang=='tr' else 'Where we have worked'}</h2><p>{'Daire büyüklüğü, o ildeki haritalı mağara kaydı sayısını gösterir. Projelerin yürütüldüğü iller fener rengiyle işaretlidir.' if lang=='tr' else 'Circle size shows the number of mapped cave records in each province. Provinces with projects are marked in lamp amber.'}</p>
<h3 class="mt">{'Yıllara göre saha raporları' if lang=='tr' else 'Field reports per year'}</h3><div class="bars" role="img" aria-label="{'Yıllara göre saha günlüğü yazısı sayısı' if lang=='tr' else 'Field journal posts per year'}">{bars}</div></div>
<div id="map" class="map" data-points='{E(mapdata)}' aria-label="{'Türkiye haritası' if lang=='tr' else 'Map of Turkey'}"></div></div></section>
{lst}
<script src="{rel(path, 'assets/leaflet/leaflet.js')}" defer></script><script src="{rel(path, 'assets/turkiye.js')}" defer></script>'''
    write(path, page(lang, path, "Araştırmalar" if lang == "tr" else "Research", body,
                     desc=("OBRUK'un projeleri: Ürgüp, Kayseri ve Gaziantep yeraltı yapıları envanterleri, Kapadokya yeraltı şehirleri, İnsuyu, Keş Dağı Düdeni ve daha fazlası." if lang == "tr" else "OBRUK projects: underground inventories of Ürgüp, Kayseri and Gaziantep, Cappadocian underground cities, Insuyu, Keş Mountain Sinkhole and more."),
                     current="arastirmalar" if lang == "tr" else "research", alt=alt, extra_head=head))

def build_reports(lang):
    path = "raporlar/" if lang == "tr" else "en/reports/"
    alt = "en/reports/" if lang == "tr" else "raporlar/"
    docs = "".join(doc_card(r[0], r[1] if lang == "tr" else r[2], fmt_date(r[3], lang) + " · " + r[4], path, lang, big=True) for r in REPORTS)
    body = page_head("OBRUK", "Raporlar" if lang == "tr" else "Reports",
                     ("Proje sonuçlarını, ölçüm ve haritaları içeren raporlarımız. Tümü ücretsiz olarak indirilebilir." if lang == "tr" else "Our project reports with survey results and maps. All are free to download."),
                     "ek foto/20250612_134800.jpg", path) + f'<section class="sec"><div class="wrap"><div class="docs docs-big">{docs}</div><p class="note">{"Raporlarımızdan alıntı yaparken lütfen kaynak gösterin: OBRUK Mağara Araştırma Grubu, rapor adı, yıl." if lang=="tr" else "When citing, please credit: OBRUK Cave Research Group, report title, year."}</p></div></section>'
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Raporlar" if lang == "tr" else "Reports",
              "hasPart": [{"@type": "Report", "name": r[1], "datePublished": r[3], "author": {"@type": "Organization", "name": SITE["name_tr"]}, "url": SITE["url"] + "/" + pdf(r[0])["path"]} for r in REPORTS if pdf(r[0])]}
    write(path, page(lang, path, "Raporlar" if lang == "tr" else "Reports", body,
                     desc=("OBRUK Mağara Araştırma Grubu raporları: Kayseri ara raporları, Gaziantep, Fırat, Küre, Kahramanmaraş, İnsuyu ve Ayvaini." if lang == "tr" else "Reports of the OBRUK Cave Research Group: Kayseri interim reports, Gaziantep, Euphrates, Küre, Kahramanmaraş, Insuyu and Ayvaini."),
                     current="raporlar" if lang == "tr" else "reports", alt=alt, jsonld=jsonld))

def build_publications(lang):
    path = "yayinlar/" if lang == "tr" else "en/publications/"
    alt = "en/publications/" if lang == "tr" else "yayinlar/"
    mag = "".join(doc_card(s, f"OBRUK {'Sayı' if lang=='tr' else 'Issue'} {n}", y, path, lang) for s, n, y in MAGAZINE)
    post = "".join(doc_card(s, t, f"{y} · {ev}" if y else ev, path, lang) for s, t, y, ev in sorted(POSTERS, key=lambda x: x[2], reverse=True))
    press = "".join(doc_card(s, t, f"{src} · {y}" if y else src, path, lang) for s, t, y, src in sorted(PRESS, key=lambda x: x[2] or "0", reverse=True))
    oth = "".join(doc_card(s, t, y, path, lang) for s, t, y in OTHER)
    tabs = [("dergi", "Dergi sayıları" if lang == "tr" else "OBRUK Magazine", mag, len(MAGAZINE)),
            ("bildiri", "Bildiri ve posterler" if lang == "tr" else "Papers and posters", post, len(POSTERS)),
            ("basin", "Basında OBRUK" if lang == "tr" else "In the press", press, len(PRESS)),
            ("diger", "Diğer yayınlar" if lang == "tr" else "Other publications", oth, len(OTHER))]
    tabnav = "".join(f'<a href="#{k}" class="chip">{E(t)} <span>{n}</span></a>' for k, t, _, n in tabs)
    secs = "".join(f'<section class="sec{" sec-alt" if i%2 else ""}" id="{k}"><div class="wrap"><div class="sec-head"><h2>{E(t)}</h2></div><div class="docs">{c}</div></div></section>' for i, (k, t, c, n) in enumerate(tabs))
    magtxt = ""
    if lang == "tr":
        magtxt = f'<section class="sec"><div class="wrap two-col"><div class="prose"><h2>OBRUK Dergisi</h2><p>OBRUK Dergisi, mağara araştırma sonuçlarıyla birlikte mağaracılık ve ilgili disiplinlerle ilgili makale ve çevirilerin yer aldığı, Türkiye\'de mağaracılık alanındaki tek süreli yayındır. 3. sayısından itibaren tüm mağaracılık gruplarının çalışmalarına açıktır.</p><p>Dergi hakemli değildir; amacı amatör grupların özveriyle yürüttüğü araştırmaların sonuçlarına —tek bir mağara haritası bile olsa— kalıcı bir yayın alanı sağlamaktır.</p><p><a href="{rel(path, "dergi-sss/")}">Dergi hakkında sık sorulan sorular →</a></p></div><div class="mag-stack">{"".join(f"<img src=\"{rel(path, pdf(s)["cover"])}\" alt=\"OBRUK {n}\" loading=\"lazy\">" for s, n, y in MAGAZINE[-3:] if pdf(s) and pdf(s)["cover"])}</div></div></section>'
    body = page_head("OBRUK", "Yayınlar" if lang == "tr" else "Publications",
                     ("Dergi sayıları, kongre bildirileri, posterler ve basında çıkan yazılar." if lang == "tr" else "Magazine issues, congress papers, posters and press coverage."),
                     None, path) + f'<nav class="chips wrap" aria-label="Bölümler">{tabnav}</nav>{magtxt}{secs}'
    write(path, page(lang, path, "Yayınlar" if lang == "tr" else "Publications", body,
                     desc=("OBRUK Dergisi'nin 7 sayısı, uluslararası kongre bildirileri ve posterler, National Geographic, Atlas ve Opera Ipogea'da çıkan yazılar." if lang == "tr" else "All 7 issues of OBRUK Magazine, international congress papers and posters, and articles in National Geographic, Atlas and Opera Ipogea."),
                     current="yayinlar" if lang == "tr" else "publications", alt=alt))

def build_inventory(lang, caves):
    path = "magara-envanteri/" if lang == "tr" else "en/inventory/"
    alt = "en/inventory/" if lang == "tr" else "magara-envanteri/"
    def num(x):
        try: return int(str(x).replace(".", "").replace(",", "").replace("m", "").strip())
        except: return None
    rows = []
    for c in sorted(caves, key=lambda c: (c["il"], c["magara"])):
        L, D = num(c["uzunluk_m"]), num(c["derinlik_m"])
        rows.append(f'<tr><td><strong>{E(c["magara"])}</strong><span class="sub">{E(c["yer"])}</span></td><td>{E(c["il"])}</td><td class="n" data-v="{L or 0}">{f"{L:,}".replace(",", ".") + " m" if L else "–"}</td><td class="n" data-v="{abs(D) if D else 0}">{(str(D) + " m") if D else "–"}</td><td>{E(c["bcra_derecesi"] or "–")}</td><td>{E(", ".join(c["cizenler"]) or "–")}</td><td data-v="{c["olcum_ay_yil"]}">{E(c["olcum_ay_yil"][:4] if c["olcum_ay_yil"] else "–")}</td></tr>')
    ils = sorted({c["il"] for c in caves})
    opts = "".join(f'<option>{E(i)}</option>' for i in ils)
    H = ["Mağara", "İl", "Uzunluk", "Derinlik", "BCRA", "Çizen", "Yıl"] if lang == "tr" else ["Cave", "Province", "Length", "Depth", "BCRA", "Surveyor", "Year"]
    th = "".join(f'<th scope="col"><button data-col="{i}">{h}</button></th>' for i, h in enumerate(H))
    longest = max(caves, key=lambda c: num(c["uzunluk_m"]) or 0); deepest = max(caves, key=lambda c: abs(num(c["derinlik_m"]) or 0))
    body = page_head("OBRUK", "Mağara Envanteri" if lang == "tr" else "Cave Inventory",
                     (f"Grubun ölçüp haritaladığı {len(caves)} mağara ve yeraltı yapısı kaydı. Tabloyu arayabilir, ile göre süzebilir ve sütunlara göre sıralayabilirsiniz." if lang == "tr" else f"{len(caves)} caves and underground structures surveyed and mapped by the group. Search, filter by province and sort by column."),
                     "ek foto/20190216_144656_IMG_6917.JPG", path) + f'''
<section class="sec"><div class="wrap">
<div class="inv-stats"><div class="stat"><span class="stat-n">{len(caves)}</span><span class="stat-l">{'kayıt' if lang=='tr' else 'records'}</span></div><div class="stat"><span class="stat-n">{len(ils)}</span><span class="stat-l">{'il' if lang=='tr' else 'provinces'}</span></div><div class="stat"><span class="stat-n">{f"{num(longest['uzunluk_m']):,}".replace(",", ".")} m</span><span class="stat-l">{E(longest['magara'])}</span></div><div class="stat"><span class="stat-n">{num(deepest['derinlik_m'])} m</span><span class="stat-l">{E(deepest['magara'])}</span></div></div>
<div class="inv-tools"><input type="search" id="inv-q" placeholder="{UI[lang]['search']}" aria-label="{'Mağara ara' if lang=='tr' else 'Search caves'}"><select id="inv-il" aria-label="{'İl' if lang=='tr' else 'Province'}"><option value="">{'Tüm iller' if lang=='tr' else 'All provinces'}</option>{opts}</select><span id="inv-count" class="meta"></span></div>
<div class="table-wrap"><table class="inv" id="inv"><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note">{'Harita görselleri zamanla bu tabloya eklenecek. BCRA: İngiliz Mağara Araştırmaları Derneği ölçüm derecesi.' if lang=='tr' else 'Map images will be added to this table over time. BCRA: British Cave Research Association survey grade.'}</p>
</div></section>'''
    write(path, page(lang, path, "Mağara Envanteri" if lang == "tr" else "Cave Inventory", body,
                     desc=("OBRUK'un ölçüp haritaladığı mağaraların aranabilir listesi: uzunluk, derinlik, BCRA derecesi, çizen ve ölçüm yılı." if lang == "tr" else "Searchable list of caves surveyed by OBRUK: length, depth, BCRA grade, surveyor and year."),
                     current="magara-envanteri" if lang == "tr" else "inventory", alt=alt))

def build_contact(lang):
    path = "iletisim/" if lang == "tr" else "en/contact/"
    alt = "en/contact/" if lang == "tr" else "iletisim/"
    T = (lambda a, b: a if lang == "tr" else b)
    body = page_head("OBRUK", T("İletişim", "Contact"),
                     T("Saha çalışmalarına katılmak, bir mağara ya da yeraltı yapısı bildirmek, iş birliği önermek veya yayınlarımız hakkında soru sormak için bize yazın.",
                       "Write to us to join fieldwork, report a cave or underground structure, propose a collaboration or ask about our publications."), None, path) + f'''
<section class="sec"><div class="wrap two-col">
<form class="contact-form" id="contact" novalidate>
<div class="f-row"><label for="c-name">{T('Adınız', 'Your name')}</label><input id="c-name" name="name" autocomplete="name" required></div>
<div class="f-row"><label for="c-mail">{T('E-posta adresiniz', 'Your email')}</label><input id="c-mail" name="email" type="email" autocomplete="email" required></div>
<div class="f-row"><label for="c-topic">{T('Konu', 'Topic')}</label><select id="c-topic" name="topic">
<option>{T('Genel soru', 'General question')}</option><option>{T('Saha çalışmalarına katılım', 'Joining fieldwork')}</option><option>{T('Mağara / yeraltı yapısı bildirimi', 'Reporting a cave or underground structure')}</option><option>{T('İş birliği önerisi', 'Collaboration proposal')}</option><option>{T('Basın', 'Press')}</option><option>{T('OBRUK Dergisi', 'OBRUK Magazine')}</option></select></div>
<div class="f-row"><label for="c-msg">{T('Mesajınız', 'Message')}</label><textarea id="c-msg" name="message" rows="6" required></textarea></div>
<p class="f-err" id="c-err" hidden>{T('Lütfen adınızı, geçerli bir e-posta adresini ve mesajınızı yazın.', 'Please enter your name, a valid email and a message.')}</p>
<button class="btn btn-primary" type="submit">{T('E-posta programında aç', 'Open in email app')}</button>
<p class="meta">{T('Form, e-posta programınızda ayamac@gmail.com adresine hazır bir ileti açar. Bilgileriniz bu sitede saklanmaz.', 'The form opens a ready-made message to ayamac@gmail.com in your email app. Nothing is stored on this site.')}</p>
</form>
<aside class="facts"><h2>{T('Doğrudan e-posta', 'Email us directly')}</h2><p><a class="big-mail" href="mailto:ayamac@gmail.com">ayamac@gmail.com</a></p>
<h2>{T('Mağara mı buldunuz?', 'Found a cave?')}</h2><p>{T('Bildirdiğiniz yerleri bilimsel amaçla araştırırız; konum bilgisini kamuya açmayız. Lütfen yapıya girmeyin ve hiçbir şeye dokunmayın.', 'We investigate reported sites for scientific purposes only and never publish their locations. Please do not enter the structure or touch anything.')}</p>
<h2>{T('Kurumlar için', 'For institutions')}</h2><p>{T('Belediyeler, müze müdürlükleri ve vakıflarla yeraltı yapıları envanteri protokolleri yürütüyoruz. Örnek çalışmalar için ', 'We run underground heritage inventory protocols with municipalities, museum directorates and foundations. See our ')}<a href="{rel(path, 'raporlar/' if lang=='tr' else 'en/reports/')}">{T('raporlarımıza', 'reports')}</a>{T(' bakabilirsiniz.', '.')}</p></aside>
</div></section>'''
    jsonld = {"@context": "https://schema.org", "@type": "ContactPage", "name": T("İletişim", "Contact"), "about": {"@type": "Organization", "name": SITE["name_" + lang], "email": SITE["email"]}}
    write(path, page(lang, path, T("İletişim", "Contact"), body, desc=T("OBRUK Mağara Araştırma Grubu ile iletişime geçin: ayamac@gmail.com", "Contact the OBRUK Cave Research Group: ayamac@gmail.com"),
                     current="iletisim" if lang == "tr" else "contact", alt=alt, jsonld=jsonld))

def build_identity(lang):
    path = "kurumsal-kimlik/" if lang == "tr" else "en/brand/"
    alt = "en/brand/" if lang == "tr" else "kurumsal-kimlik/"
    T = (lambda a, b: a if lang == "tr" else b)
    K = "img/kimlik/"
    def kb(f): return f"{os.path.getsize(OUT + K + f)/1e3:.0f} KB" if os.path.getsize(OUT + K + f) < 1e6 else mb(os.path.getsize(OUT + K + f))
    def dl(f, label): return f'<a class="btn-dl" href="{rel(path, K + f)}" download>{label}<span>{kb(f)}</span></a>'
    items = [
        ("obruk-logo-siyah-onizleme.png", False, T("Logo · siyah", "Logo · black"), T("Açık zeminler için", "For light backgrounds"),
         [dl("obruk-logo-siyah.svg", "SVG"), dl("obruk-logo-siyah.png", "PNG 4000 px"), dl("obruk-logo-beyaz-zemin.jpg", T("JPG beyaz zemin", "JPG on white"))]),
        ("obruk-logo-krem-onizleme.png", True, T("Logo · beyaz", "Logo · white"), T("Koyu zeminler ve fotoğraf üzeri için", "For dark backgrounds and photos"),
         [dl("obruk-logo-beyaz.svg", "SVG"), dl("obruk-logo-beyaz.png", "PNG 4000 px"), dl("obruk-logo-krem.png", T("PNG krem", "PNG cream"))]),
        ("omag-amblem-siyah-onizleme.png", False, T("o'mag amblemi · siyah", "o'mag mark · black"), T("Küçük alanlar, sosyal medya, ekipman", "Small spaces, social media, gear"),
         [dl("omag-amblem-siyah.svg", "SVG"), dl("omag-amblem-siyah.png", "PNG 4000 px")]),
        ("omag-amblem-krem-onizleme.png", True, T("o'mag amblemi · beyaz", "o'mag mark · white"), T("Koyu zeminler için", "For dark backgrounds"),
         [dl("omag-amblem-beyaz.svg", "SVG"), dl("omag-amblem-beyaz.png", "PNG 4000 px"), dl("omag-amblem-krem.png", T("PNG krem", "PNG cream"))]),
    ]
    cards = "".join(f'<article class="logo-card"><div class="logo-prev{" dark" if dark else ""}"><img src="{rel(path, K + p)}" alt="{E(t)}" loading="lazy"></div><div class="logo-body"><h3>{E(t)}</h3><p class="meta">{E(d)}</p><div class="dl-row">{"".join(b)}</div></div></article>' for p, dark, t, d, b in items)
    colors = [("#1E1B17", T("Bazalt", "Basalt")), ("#F4EEE4", T("Tüf", "Tuff")), ("#E9A23B", T("Fener", "Lamp")), ("#A3452A", T("Hematit", "Hematite")), ("#6B6258", T("Kül", "Ash"))]
    sw = "".join(f'<div class="swatch"><span style="background:{c}"></span><strong>{E(n)}</strong><code>{c}</code></div>' for c, n in colors)
    rules = [T("Logonun oranlarını bozmayın, eğmeyin, döndürmeyin.", "Do not stretch, skew or rotate the logo."),
             T("Yalnızca siyah, beyaz veya krem renklerini kullanın; efekt, gölge ya da çerçeve eklemeyin.", "Use only the black, white or cream versions; do not add effects, shadows or outlines."),
             T("Logonun çevresinde en az \"o\" harfi yüksekliği kadar boşluk bırakın.", "Leave clear space around the logo at least the height of the letter \"o\"."),
             T("Basılı işlerde SVG veya 4000 px PNG dosyasını kullanın; ekran görüntüsü almayın.", "For print, use the SVG or the 4000 px PNG — never a screenshot."),
             T("Ortak çalışma, etkinlik ve yayınlarda kullanım için bize haber vermeniz yeterli.", "For joint projects, events and publications, simply let us know.")]
    rl = "".join(f"<li>{E(r)}</li>" for r in rules)
    body = page_head("OBRUK", T("Logo ve Kurumsal Kimlik", "Logo and Brand"),
                     T("OBRUK logosunu ortak projeler, haberler ve yayınlar için yüksek çözünürlükte indirebilirsiniz. PNG dosyalarının arka planı şeffaftır.",
                       "Download the OBRUK logo in high resolution for joint projects, news and publications. PNG files have transparent backgrounds."), None, path) + f'''
<section class="sec"><div class="wrap"><div class="pack"><div><h2>{T("Tüm logo paketi", "Complete logo package")}</h2><p>{T("Bütün renk ve biçimleri (SVG, PNG, JPG) tek dosyada indirin.", "All colours and formats (SVG, PNG, JPG) in one file.")}</p></div><a class="btn btn-primary" href="{rel(path, K + "obruk-logo-paketi.zip")}" download>{T("Paketi indir", "Download package")} · ZIP {kb("obruk-logo-paketi.zip")}</a></div>
<div class="logo-grid">{cards}</div></div></section>
<section class="sec sec-alt"><div class="wrap two-col"><div><h2>{T("Kullanım kuralları", "Usage guidelines")}</h2><ul class="rules">{rl}</ul><p class="meta">{T("Sorularınız için:", "Questions:")} <a href="mailto:ayamac@gmail.com">ayamac@gmail.com</a></p></div>
<div><h2>{T("Renkler", "Colours")}</h2><div class="swatches">{sw}</div><p class="meta">{T("Yazı tipleri: Source Serif 4 (başlık), Inter (metin).", "Typefaces: Source Serif 4 (headings), Inter (body).")}</p></div></div></section>'''
    write(path, page(lang, path, T("Logo ve Kurumsal Kimlik", "Logo and Brand"), body,
                     desc=T("OBRUK Mağara Araştırma Grubu logosu: SVG ve yüksek çözünürlüklü PNG indirme, renkler ve kullanım kuralları.", "OBRUK Cave Research Group logo: SVG and high-resolution PNG downloads, colours and usage guidelines."),
                     current="", alt=alt))

def build_join(pages):
    path = "katil/"
    eg = pages.get("sayfalar/taslaklar/egitim-programlari.md")
    body = page_head("OBRUK", "Bize katılın", "OBRUK'u güçlü kılan, ona emek veren mağaracılardır. Gelecek kuşaklara güçlü bir OBRUK bırakmak için yeni ellere ihtiyacımız var.", "ek foto/20250612_142712.jpg", path) + f'''
<section class="sec"><div class="wrap grid g3 whats">
<div class="what"><h3>Sahaya gelin</h3><p>Ölçüm ve haritalama çalışmalarımıza katılın. Deneyimli üyelerin yanında topografya, çizim ve belgeleme öğrenirsiniz. Tek ip tekniği (SRT) deneyimi dikey mağaralar için gereklidir.</p></div>
<div class="what"><h3>Çizin ve yazın</h3><p>Haritaların temize çekilmesi, raporların ve OBRUK Dergisi yazılarının hazırlanması en az saha kadar emek ister. Grafik, CBS ya da editörlük becerileriniz çok değerli.</p></div>
<div class="what"><h3>Destek olun</h3><p>OBRUK kâr amacı gütmez; dergi ve saha giderleri üyelerin katkılarıyla karşılanır. Kurumsal destek ve ortak proje önerilerinize açığız.</p></div>
</div></section>
<section class="sec sec-alt"><div class="wrap narrow prose"><h2>Etik anlayışımız</h2><p>Mağaralar ve yeraltı yapıları yenilenemez. Bu yüzden ekibimize katılan herkesten <a href="{rel(path, 'magaracilarin-sorumluluklari/')}">mağaracıların sorumluluklarını</a> benimsemesini bekliyoruz: hiçbir şeyi kırmamak, almamak, iz bırakmamak; bulguları zamanında ve eksiksiz paylaşmak; keşfedilen yerlerin konumlarını korumak.</p>{md_to_html(eg["body"], path) if eg else ""}
<p><a class="btn btn-primary" href="{rel(path, 'iletisim/')}">Bize yazın</a></p></div></section>'''
    write(path, page("tr", path, "Bize katılın", body, desc="OBRUK Mağara Araştırma Grubu'na katılın: saha çalışmaları, haritalama, yayın ve destek.", current=""))

def build_journal(posts):
    path = "saha-gunlugu/"
    years = sorted({p["year"] for p in posts}, reverse=True)
    chips = '<button class="chip is-on" data-y="">Tümü</button>' + "".join(f'<button class="chip" data-y="{y}">{y}</button>' for y in years)
    kinds = '<button class="chip is-on" data-k="">Hepsi</button><button class="chip" data-k="haber">Saha günlüğü</button><button class="chip" data-k="kose">Köşe yazıları</button>'
    cards = "".join(card_post(p, path).replace('<article class="card post-card">', f'<article class="card post-card" data-y="{p["year"]}" data-k="{p["kind"]}" data-t="{E(tr_lower(p["title"]))}">') for p in posts)
    body = page_head("Arşiv", "Saha Günlüğü", f"2009'dan 2021'e {len(posts)} yazı: saha çalışmaları, ekspedisyonlar, kongreler ve köşe yazıları.", None, path) + f'''
<section class="sec"><div class="wrap"><div class="filters"><input type="search" id="j-q" placeholder="Yazılarda ara…" aria-label="Yazılarda ara"><div class="chips-row" id="j-k">{kinds}</div><div class="chips-row" id="j-y">{chips}</div></div><div class="grid g3" id="journal">{cards}</div><p class="meta" id="j-empty" hidden>Eşleşen yazı bulunamadı.</p></div></section>'''
    write(path, page("tr", path, "Saha Günlüğü", body, desc="OBRUK Mağara Araştırma Grubu'nun 2009–2021 saha çalışmaları, ekspedisyonları ve köşe yazıları arşivi.", current="saha-gunlugu"))
    # tekil yazılar
    for i, p in enumerate(posts):
        pp = p["slug"] + "/"
        h = md_to_html(p["body"], pp)
        prev = posts[i + 1] if i + 1 < len(posts) else None
        nxt = posts[i - 1] if i > 0 else None
        pn = '<nav class="prevnext">' + (f'<a href="{rel(pp, prev["slug"] + "/")}"><span>← Önceki</span>{E(prev["title"])}</a>' if prev else "<span></span>") + (f'<a class="nx" href="{rel(pp, nxt["slug"] + "/")}"><span>Sonraki →</span>{E(nxt["title"])}</a>' if nxt else "") + "</nav>"
        tag = "Köşe yazısı" if p["kind"] == "kose" else "Saha günlüğü"
        cover = p["cover"]
        art = f'''<article class="article"><header class="art-head wrap narrow"><p class="kicker"><a href="{rel(pp, 'saha-gunlugu/')}">{tag}</a></p><h1>{E(p['title'])}</h1><p class="meta"><time datetime="{p['date']}">{fmt_date(p['date'])}</time>{' · Ali Yamaç' if p['kind']=='kose' else ''}</p></header>
<div class="wrap narrow prose">{h}</div><div class="wrap narrow">{pn}</div></article>'''
        jsonld = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "datePublished": p["date"], "inLanguage": "tr",
                  "author": {"@type": "Organization", "name": SITE["name_tr"]}, "publisher": {"@type": "Organization", "name": SITE["name_tr"], "logo": {"@type": "ImageObject", "url": SITE["url"] + "/img/logo.png"}},
                  "mainEntityOfPage": SITE["url"] + "/" + pp}
        if cover: jsonld["image"] = SITE["url"] + "/" + cover["src"]
        write(pp, page("tr", pp, p["title"], art, desc=excerpt(h, 155), current="saha-gunlugu", og_img=cover["src"] if cover else None, jsonld=jsonld))

GROUPS = {
    "bilgi-bankasi": ("Bilgi Bankası", "Mağaracılık üzerine sık sorulan sorular, rekorlar, malzeme önerileri, kütüphane ve nostalji yazıları.",
                      ["sss", "en-derin-ve-en-uzun", "malzeme-onerileri", "kutuphane", "dergi-sss", "baglantilar", "dr-temucin-aygen-1921-2003", "turk-basininda-ilk-defa", "45-yil-once-dunya", "siradisi-bir-yil-1970", "yarimburgaz-magarasi", "sevgili-defineciler", "magaracilar-icin-2019-burc-yorumlari", "obruk-original"]),
    "koruma": ("Koruma ve Etik", "Mağaralar ve yeraltı yapıları geri getirilemez. Koruma üzerine yazılarımız ve tahribatı belgeleyen Utanç Sayfası.",
               ["magaracilarin-sorumluluklari", "turizme-acilmis-magaralar-1", "turizme-acilmis-magaralar-2", "bir-turizm-katliami-cal-magarasi", "havranin-yarasalari", "ballikaya-bitti", "yavru-yarasalar-klinikte", "utanc-sayfasi"]),
}

def build_pages(pages, caves):
    by_slug = {p["slug"]: p for p in pages.values()}
    skip = {"hakkimizda", "projeler", "raporlar", "bize-ulasin", "magara-haritasi", "yayinlanmis-sayilar", "sempozyum-bildiri-poster", "dergi-yazilari", "magaracilik-sinavi", "koruma", "etkinlikler-takvimi", "egitim-programlari", "obruk-sayi-1", "gelecek-sayi"}
    eng = {"underground-structures-inventory-project-of-kayseri", "castle-of-gaziantep", "ahmet-celebi-qastel-of-gaziantep"}
    parent = {}
    for g, (_, _, sl) in GROUPS.items():
        for s in sl: parent[s] = g
    for k, p in pages.items():
        s = p["slug"]
        if s in skip: continue
        if "/utanc-sayfasi/" in k: parent.setdefault(s, "utanc-sayfasi")
        path = s + "/"
        lang = "en" if s in eng else "tr"
        h = md_to_html(p["body"], path)
        if s == "utanc-sayfasi":
            subs = [q for kk, q in pages.items() if "/utanc-sayfasi/" in kk]
            h += '<div class="grid g2 shame">' + "".join(f'<a class="shame-card" href="{rel(path, q["slug"] + "/")}"><h3>{E(q["title"])}</h3><p>{E(excerpt(md_to_html(q["body"], path), 120))}</p></a>' for q in subs) + "</div>"
        g = parent.get(s)
        crumb = ""
        if g in GROUPS: crumb = f'<a href="{rel(path, g + "/")}">{GROUPS[g][0]}</a>'
        elif g == "utanc-sayfasi": crumb = f'<a href="{rel(path, "utanc-sayfasi/")}">Utanç Sayfası</a>'
        elif lang == "en": crumb = f'<a href="{rel(path, "en/research/")}">Research</a>'
        title = p["title"] if lang == "tr" else p["title"].title() if p["title"].isupper() else p["title"]
        body = f'<article class="article"><header class="art-head wrap narrow"><p class="kicker">{crumb or "OBRUK"}</p><h1>{E(title)}</h1></header><div class="wrap narrow prose">{h}</div></article>'
        write(path, page(lang, path, title, body, desc=excerpt(h, 155), current=g or ""))
    # kütüphane
    path = "kutuphane/"
    books = list(csv.DictReader(open(SRC + "drupal_arsivi/veri/kutuphane.csv", encoding="utf-8-sig")))
    bk = "".join(f'<article class="book"><h3>{E(b["kitap"].title() if b["kitap"].isupper() else b["kitap"])}</h3>{f"<p class=\"sub\">{E(b["alt_baslik"])}</p>" if b["alt_baslik"] else ""}<p class="meta">{E(b["yazarlar"])}{" · " + E(b["yayinevi"]) if b["yayinevi"] else ""}{" · " + b["yil"] if b["yil"] else ""}{" · " + b["sayfa"] + " s." if b["sayfa"] else ""}</p><p>{E(b["aciklama"])}</p></article>' for b in books)
    body = f'<article class="article"><header class="art-head wrap narrow"><p class="kicker"><a href="{rel(path, "bilgi-bankasi/")}">Bilgi Bankası</a></p><h1>Kütüphane</h1><p class="lead">Grup kütüphanemizden {len(books)} kitap ve tanıtım notları.</p></header><div class="wrap narrow books">{bk}</div></article>'
    write(path, page("tr", path, "Kütüphane", body, desc="OBRUK grup kütüphanesinden mağaracılık kitapları ve tanıtımları.", current="bilgi-bankasi"))
    # SSS (tam)
    path = "sss/"
    _, t = read_md(SRC + "drupal_arsivi/veri/sss_tam.md") if False else ({}, open(SRC + "drupal_arsivi/veri/sss_tam.md", encoding="utf-8").read())
    parts = re.split(r"\n## ", "\n" + re.sub(r"^#\s.*\n", "", t))
    qa = "".join(f'<details class="qa"><summary>{E(x.split(chr(10),1)[0].strip())}</summary><div class="prose">{md_to_html(x.split(chr(10),1)[1] if chr(10) in x else "", path)}</div></details>' for x in parts if x.strip())
    body = f'<article class="article"><header class="art-head wrap narrow"><p class="kicker"><a href="{rel(path, "bilgi-bankasi/")}">Bilgi Bankası</a></p><h1>Sıkça Sorulan Sorular</h1><p class="lead">Mağaracılık, koruma, malzeme ve grubumuz hakkında en çok sorulanlar.</p></header><div class="wrap narrow">{qa}</div></article>'
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": x.split("\n", 1)[0].strip(), "acceptedAnswer": {"@type": "Answer", "text": excerpt(md_to_html(x.split("\n", 1)[1], path), 600)}} for x in parts if x.strip() and "\n" in x][:40]}
    write(path, page("tr", path, "Sıkça Sorulan Sorular", body, desc="Mağaracılık ve OBRUK hakkında sıkça sorulan sorular ve cevapları.", current="bilgi-bankasi", jsonld=faq_ld))
    # grup sayfaları
    for g, (title, lead, sl) in GROUPS.items():
        path = g + "/"
        items = []
        for s in sl:
            if s == "kutuphane": items.append(("Kütüphane", "Grup kütüphanemizden kitaplar ve tanıtımları.", s)); continue
            if s == "sss": items.append(("Sıkça Sorulan Sorular", "Mağaracılık, koruma ve grubumuz hakkında en çok sorulanlar.", s)); continue
            q = by_slug.get(s)
            if not q: continue
            items.append((q["title"], excerpt(md_to_html(q["body"], path), 120), s))
        cards = "".join(f'<a class="shame-card" href="{rel(path, s + "/")}"><h3>{E(t)}</h3><p>{E(d)}</p></a>' for t, d, s in items)
        extra = ""
        if g == "bilgi-bankasi":
            extra = f'<a class="shame-card accent" href="{rel(path, "magaracilik-sinavi/")}"><h3>Mağaracılık Sınavı</h3><p>51 soruluk havuzdan rastgele 10 soru. Kendinizi deneyin.</p></a>'
        body = page_head("Arşiv", title, E(lead), "ek foto/20250218_151807.jpg" if g == "koruma" else None, path) + f'<section class="sec"><div class="wrap grid g3 shame">{extra}{cards}</div></section>'
        write(path, page("tr", path, title, body, desc=lead, current=g))

def build_quiz():
    path = "magaracilik-sinavi/"
    qs = json.load(open(SRC + "drupal_arsivi/veri/magaracilik_sinavi_tam.json", encoding="utf-8"))
    data = [{"q": q["soru"], "o": [o.rstrip(",") for o in q["secenekler"]], "a": [o.rstrip(",") for o in q["dogru"]]} for q in qs if q.get("secenekler")]
    body = page_head("Bilgi Bankası", "Mağaracılık Sınavı", f"{len(data)} soruluk havuzdan her seferinde rastgele 10 soru. Mağaracılık tarihi, jeoloji, teknik ve rekorlar.", None, path) + f'''
<section class="sec"><div class="wrap narrow"><div id="quiz" class="quiz" data-q='{E(json.dumps(data, ensure_ascii=False))}'><p class="meta">Sınav yükleniyor…</p></div></div></section>'''
    write(path, page("tr", path, "Mağaracılık Sınavı", body, desc="Mağaracılık bilginizi test edin: OBRUK'un hazırladığı 51 soruluk mağaracılık sınavı.", current="magaracilik-sinavi"))

def build_redirects():
    """Eski adresler: yeni sayfaya yönlendirme."""
    simple = {"magaracilar": "hakkimizda/", "en/cavers": "en/about/", "projeler": "arastirmalar/", "bize-ulasin": "iletisim/", "magara-haritasi": "magara-envanteri/", "yayinlanmis-sayilar": "yayinlar/#dergi",
              "sempozyum-bildiri-poster": "yayinlar/#bildiri", "dergi-yazilari": "yayinlar/#basin", "dergi": "yayinlar/", "calismalar": "arastirmalar/",
              "eglencelik": "bilgi-bankasi/", "meraklisina": "bilgi-bankasi/", "nostalji": "bilgi-bankasi/", "etkinlikler-takvimi": "saha-gunlugu/",
              "haberler": "saha-gunlugu/", "obruk-sayi-1": "yayinlar/#dergi", "gelecek-sayi": "yayinlar/#dergi", "egitim-programlari": "katil/",
              "calisma-bolgelerimiz": "arastirmalar/", "haritalar": "magara-envanteri/", "tr": "", "en/home": "en/"}
    rows = list(csv.DictReader(open(SRC + "veri/url_esleme.csv", encoding="utf-8-sig")))
    for r in rows:
        tgt = POSTMAP.get(r["yeni_dosya"])
        if not tgt or not os.path.exists(OUT + tgt + "index.html"):
            s = urllib.parse.urlparse(r["eski_url"]).path.strip("/")
            tgt = simple.get(s)
        if not tgt and tgt != "": continue
        node = r.get("eski_drupal_node", "")
        if node:
            simple[urllib.parse.urlparse(node).path.strip("/")] = tgt
    n = 0
    for old, tgt in simple.items():
        if os.path.exists(OUT + old + "/index.html"): continue
        to = rel(old + "/", tgt) if tgt else rel(old + "/", "")
        canon = SITE["url"] + "/" + tgt
        write(old + "/", f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Yönlendiriliyor…</title><link rel="canonical" href="{canon}"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={to}"></head><body><p><a href="{to}">Sayfa taşındı, buraya tıklayın.</a></p></body></html>')
        n += 1
    return n

def build_404():
    body = f'<section class="page-head"><div class="wrap"><p class="kicker">404</p><h1>Bu galeri haritada yok</h1><p class="lead">Aradığınız sayfa taşınmış ya da hiç ölçülmemiş olabilir. <a href="/">Ana sayfaya dönün</a> veya <a href="/saha-gunlugu/">saha günlüğünde</a> arayın.</p></div></section>'
    h = page("tr", "404.html", "Sayfa bulunamadı", body)
    SITEMAP.remove("404.html")
    # 404 her derinlikte çalışsın diye mutlak yollar
    h = h.replace('href="assets/', 'href="/assets/').replace('src="assets/', 'src="/assets/').replace('href="favicon', 'href="/favicon')
    open(OUT + "404.html", "w", encoding="utf-8").write(h)

def build_meta():
    urls = "".join(f"<url><loc>{SITE['url']}/{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in sorted(set(SITEMAP)))
    open(OUT + "sitemap.xml", "w", encoding="utf-8").write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    open(OUT + "robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n")
    open(OUT + ".nojekyll", "w").write("")

# ------------------------------------------------------------------ ana akış
def main():
    for d in glob.glob(OUT + "*"):
        b = os.path.basename(d)
        if b in ("medya", "img", "pdf", "assets", "favicon.svg", "_kaynak", "README.md"): continue
        shutil.rmtree(d) if os.path.isdir(d) else os.remove(d)
    prep_pdfs()
    posts = load_posts(); pages = load_pages(); caves = load_caves()
    for lang in ("tr", "en"):
        build_home(lang, posts, caves, None)
        build_about(lang, pages); build_research(lang, posts, caves)
        build_reports(lang); build_publications(lang); build_inventory(lang, caves); build_contact(lang); build_identity(lang)
    build_join(pages); build_journal(posts); build_pages(pages, caves); build_quiz()
    n = build_redirects(); build_404(); build_meta()
    print("posts", len(posts), "pages", len(pages), "caves", len(caves), "redirects", n, "urls", len(set(SITEMAP)))

if __name__ == "__main__":
    main()
