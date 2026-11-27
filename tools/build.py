"""
Navera Marketing - static site builder (src/ -> docs/).

    py tools/build.py            build docs/ and run the audit
    py tools/build.py --images   also (re)render favicon PNGs + per-page share images (needs Chrome + internet)

Pages live in src/pages/*.html. Each starts with a JSON front-matter comment:

    <!--page { "path": "seo-company-sonipat/", "title": "...", "description": "...", ... } -->

Body placeholders:
    {{root}}            relative prefix to the site root ("" or "../")
    {{icon:name}}       <svg><use href="#i-name"></svg> from partials/icons.html
    {{part:name}}       include partials/name.html
    {{art:name}}        include partials/art-name.html (service illustration)
    {{wa:N}} {{tel:N}} {{ph:N}}   WhatsApp link / tel number / display number for phone N (0-2)
    {{faq}} {{cta}} {{related}} {{crumbs}} {{services-cards}} {{insta}} {{instahandle}}

Change the domain in src/site.json (customDomain) and rebuild: canonicals, OG, sitemap,
JSON-LD and CNAME all follow.
"""
import hashlib
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "docs"
TOOLS = ROOT / "tools"

site = json.loads((SRC / "site.json").read_text(encoding="utf-8"))
if site.get("customDomain"):
    BASE = "https://" + site["customDomain"].strip("/") + "/"
else:
    BASE = site["baseUrl"].rstrip("/") + "/"

PARTS = {p.stem: p.read_text(encoding="utf-8") for p in (SRC / "partials").glob("*.html")}

SERVICES = [
    # path, short name (menus), blurb, icon, schema serviceType  (order + names follow the 2026 proposal)
    ("social-media-marketing-sonipat/", "Social Media Management", "Instagram & Facebook, planned and managed", "social", "Social media marketing"),
    ("video-production-sonipat/", "Reels & Video Production", "On-location shoots, reels and edits", "video", "Video production"),
    ("graphic-design-branding-sonipat/", "Graphic Design & Branding", "Creatives, campaigns and visual identity", "pen", "Graphic design and branding"),
    ("website-designing-company-sonipat/", "Website Development", "Business, catalogue and e-commerce sites", "globe", "Website design and development"),
    ("google-ads-meta-ads-sonipat/", "Paid Advertising", "Meta and Google campaigns that bring enquiries", "ads", "Online advertising"),
    ("seo-company-sonipat/", "SEO & Google Business Profile", "Get found on Google search and Maps", "seo", "Search engine optimization"),
]

PLANS = [
    # name, price (INR / month), one-liner
    ("Essential", 9999, "For a consistent and professional social presence."),
    ("Business Growth", 19999, "For stronger storytelling and local visibility."),
    ("Premium Growth", 24999, "For brands ready for a fuller content push."),
]
WEB_PLANS = [
    ("Basic Website", 6999, "A clean online home for your business."),
    ("Catalogue Website", 14999, "Showcase your products or services in one place."),
    ("E-commerce Website", 29999, "A store for customers who want to shop online."),
]

AREAS = ["Sonipat", "Kundli", "Murthal", "Rai", "Ganaur", "Gohana", "Kharkhoda"]


def esc(s):
    return html.escape(s, quote=True)


def icon(name, cls="ic"):
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} aria-hidden="true"><use href="#i-{name}"/></svg>'


def wa_link(i, text=None):
    p = site["phones"][i]
    return "https://wa.me/" + p["wa"] + "?text=" + urllib.parse.quote(text or site["waText"])


def rel_prefix(path):
    return "../" * path.count("/")


def og_slug(path):
    return "home" if path in ("", "404.html") else path.strip("/").replace("/", "-")


# ---------------------------------------------------------------------------
# blocks generated from data

def services_menu(root):
    out = []
    for path, name, blurb, ic, _ in SERVICES:
        out.append(f'<a href="{root}{path}"><span class="ic-wrap">{icon(ic)}</span><span><b>{esc(name)}</b><small>{esc(blurb)}</small></span></a>')
    return "\n            ".join(out)


def services_list(root):
    return "".join(f'<li><a href="{root}{p}">{esc(n)}</a></li>' for p, n, *_ in SERVICES)


def services_cards(root):
    cards = []
    for i, (path, name, blurb, ic, _) in enumerate(SERVICES, 1):
        cards.append(
            f'<a class="card glass rv" style="--d:{(i - 1) % 3 * 0.08:.2f}s" href="{root}{path}">'
            f'<span class="num" aria-hidden="true">0{i}</span>'
            f'<span class="ic-wrap">{icon(ic)}</span>'
            f'<h3>{esc(name)}</h3><p>{esc(SERVICE_CARD_COPY[path])}</p>'
            f'<span class="link-arrow">Explore {icon("arrow")}</span></a>'
        )
    return "\n".join(cards)


SERVICE_CARD_COPY = {
    "social-media-marketing-sonipat/": "Content planning, monthly calendars, captions and publishing for Instagram and Facebook, so your brand stays active, consistent and recognisable.",
    "video-production-sonipat/": "Reel concepts, on-location shoots in Sonipat and sharp edits: product, service and behind-the-scenes videos that make people pause and watch.",
    "graphic-design-branding-sonipat/": "Promotional creatives, stories, banners and festive campaign assets with one clear visual direction across every post.",
    "website-designing-company-sonipat/": "Responsive business websites, product catalogues and e-commerce stores that help customers explore, trust and enquire.",
    "google-ads-meta-ads-sonipat/": "Meta and Google campaign setup, audience and creative testing, monitoring and clear performance summaries.",
    "seo-company-sonipat/": "Google Business Profile setup and support, local search foundations and on-page SEO so nearby customers find you first.",
}


def related(root, current):
    out = []
    for path, name, blurb, ic, _ in SERVICES:
        if path == current:
            continue
        out.append(f'<a class="glass rv" href="{root}{path}"><span class="ic-wrap">{icon(ic)}</span><span><b>{esc(name)}</b><small>{esc(blurb)}</small></span></a>')
    return (
        '<section class="section section--tight" aria-labelledby="rel-title"><div class="wrap">'
        '<div class="section-head section-head--left"><p class="eyebrow eyebrow--left">More from Navera</p>'
        '<h2 id="rel-title">Other services in <em class="accent">Sonipat</em></h2></div>'
        f'<div class="related">{"".join(out)}</div></div></section>'
    )


# ---------------------------------------------------------------------------
# portfolio (src/work.json -> /work/ page + home teaser)

WORK = json.loads((SRC / "work.json").read_text(encoding="utf-8"))
PROJECTS = WORK["projects"]
KIND_LABEL = {"client": "Client website", "concept": "Concept demo", "product": "Web app"}


def site_host(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc.removeprefix("www.")
    if host.endswith("github.io"):
        host += "/" + u.path.strip("/").split("/")[0]
    return host


def own_domain(p):
    return not urllib.parse.urlparse(p["url"]).netloc.endswith("github.io")


def where(p):
    return " &middot; ".join(esc(x) for x in (p["industry"], p.get("city")) if x)


def shot_img(root, p, cls="", eager=False, sizes="(max-width: 640px) 92vw, (max-width: 900px) 46vw, 380px"):
    base = f'{root}assets/img/work/{p["slug"]}'
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{base}-sm.jpg" srcset="{base}-sm.jpg 640w, {base}.jpg 1280w" sizes="{sizes}" '
            f'width="1280" height="800" alt="{esc(p["name"])} website home page, designed and built by Navera Marketing" {load} decoding="async">')


def browser(root, p, **kw):
    return (f'<div class="browser"><div class="bar" aria-hidden="true"><i></i><i></i><i></i>'
            f'<span>{esc(site_host(p["url"]))}</span></div>{shot_img(root, p, **kw)}</div>')


def phone_shot(root, p, eager=False):
    load = "" if eager else ' loading="lazy"'
    return (f'<div class="mphone"><img src="{root}assets/img/work/{p["slug"]}-m.jpg" width="360" height="780" '
            f'alt="{esc(p["name"])} website on a phone"{load} decoding="async"></div>')


def wa_like(p):
    return esc(wa_link(0, f"Hi Navera Marketing! I saw the {p['name']} website in your portfolio. I'd like a website like this for my business."))


def work_cases(root):
    out = []
    for i, p in enumerate([p for p in PROJECTS if p.get("featured")], 1):
        pts = "".join(f"<li>{icon('check')}<span>{esc(x)}</span></li>" for x in p.get("points", []))
        tags = "".join(f"<li>{esc(t)}</li>" for t in p["tags"])
        out.append(
            f'<article class="case{" case--flip" if i % 2 == 0 else ""}" aria-labelledby="case-{p["slug"]}">'
            f'<a class="case-media rv" href="{p["url"]}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true">'
            f'{browser(root, p, sizes="(max-width: 900px) 92vw, 640px")}{phone_shot(root, p)}</a>'
            f'<div class="case-copy rv" style="--d:.1s">'
            f'<span class="case-num" aria-hidden="true">0{i}</span>'
            f'<p class="wc-meta">{KIND_LABEL[p["kind"]]} &middot; {where(p)}</p>'
            f'<h3 id="case-{p["slug"]}">{esc(p["name"])}</h3>'
            f'<p class="case-sum">{esc(p["summary"])}</p>'
            f'<ul class="case-pts">{pts}</ul>'
            f'<ul class="wc-tags">{tags}</ul>'
            f'<div class="btn-row"><a class="btn btn--chrome btn--sm" href="{p["url"]}" target="_blank" rel="noopener">'
            f'Visit live site {icon("ext")}</a>'
            f'<a class="btn btn--ghost btn--sm" href="{wa_like(p)}" target="_blank" rel="noopener">{icon("wa")} I want one like this</a></div>'
            f'</div></article>'
        )
    return "\n".join(out)


def work_card(root, p, i, eager=False):
    tags = "".join(f"<li>{esc(t)}</li>" for t in p["tags"])
    kind = f'<span class="wc-kind wc-kind--{p["kind"]}">{KIND_LABEL[p["kind"]]}</span>'
    return (
        f'<a class="work-card rv" style="--d:{i % 3 * 0.08:.2f}s" href="{p["url"]}" target="_blank" rel="noopener" data-cats="{" ".join(p["cats"])}">'
        f'<div class="wc-media">{browser(root, p, eager=eager)}{kind}</div>'
        f'<div class="wc-body"><p class="wc-meta">{where(p)}</p>'
        f'<h3>{esc(p["name"])} {icon("ext", "ic wc-ext")}</h3>'
        f'<p>{esc(p["summary"])}</p><ul class="wc-tags">{tags}</ul></div></a>'
    )


def work_grid(root):
    cards = [work_card(root, p, i) for i, p in enumerate(PROJECTS)]
    nxt = esc(wa_link(0, "Hi Navera Marketing! I saw your portfolio and I'd like a website for my business."))
    cards.append(
        f'<a class="work-card work-card--next rv" href="{nxt}" target="_blank" rel="noopener" data-cats="*">'
        f'<svg class="spark-big twinkle" aria-hidden="true"><use href="#i-spark"/></svg>'
        f'<p class="wc-meta">Project {len(PROJECTS) + 1:02d}</p>'
        f'<h3>Your business, <em class="accent">next.</em></h3>'
        f'<p>Tell us what you sell and who you sell to. We&rsquo;ll suggest the right kind of website and give you a clear price.</p>'
        f'<span class="btn btn--chrome btn--sm">{icon("wa")} Start on WhatsApp</span></a>'
    )
    return "\n".join(cards)


def work_filters():
    out = []
    for key, label in WORK["filters"]:
        n = len(PROJECTS) if key == "all" else sum(key in p["cats"] for p in PROJECTS)
        out.append(f'<button type="button" class="chip-btn" data-filter="{key}" aria-pressed="{"true" if key == "all" else "false"}">'
                   f'{esc(label)} <span>{n}</span></button>')
    return "".join(out)


def work_stats():
    clients = sum(p["kind"] == "client" for p in PROJECTS)
    stats = [
        (len(PROJECTS), "projects live online"),
        (clients, "client brands"),
        (sum(own_domain(p) for p in PROJECTS), "on their own domain"),
        (len(WORK["filters"]) - 1, "kinds of business"),
    ]
    return "".join(f'<div><b>{n}</b><span>{esc(t)}</span></div>' for n, t in stats)


def work_marquee():
    names = "".join(f"<li>{esc(p['name'])} {icon('spark')}</li>" for p in PROJECTS if p["kind"] == "client")
    return f'<ul>{names}</ul><ul>{names}</ul>'


def work_teaser(root):
    feat = [p for p in PROJECTS if p.get("featured")][:3]
    return "\n".join(work_card(root, p, i) for i, p in enumerate(feat))


def work_hero(root):
    by = {p["slug"]: p for p in PROJECTS}
    a, b, c = (by[s] for s in WORK.get("hero", ["aggarwal-properties", "chaudhary-nutrition", "rohtak-property-point"]))
    return (f'<div class="work-stack rv" style="--d:.15s" aria-hidden="true">'
            f'<div class="ws-back">{browser(root, b, sizes="420px")}</div>'
            f'<div class="ws-front">{browser(root, a, eager=True, sizes="(max-width: 900px) 80vw, 520px")}</div>'
            f'{phone_shot(root, c, eager=True)}</div>')


def faq_block(fm):
    items = fm.get("faq") or []
    if not items:
        return ""
    title = fm.get("faqTitle", 'Questions, <em class="accent">answered</em>')
    rows = []
    for q, a in items:
        paras = "".join(f"<p>{p}</p>" for p in a.split("\n\n"))
        rows.append(f'<details class="rv"><summary>{q}<span class="pm" aria-hidden="true"></span></summary><div class="ans">{paras}</div></details>')
    return (
        '<section class="section" id="faq" aria-labelledby="faq-title"><div class="wrap">'
        '<div class="section-head"><p class="eyebrow"><svg class="spark" aria-hidden="true"><use href="#i-spark"/></svg> FAQ</p>'
        f'<h2 id="faq-title">{title}</h2></div>'
        f'<div class="faq">{"".join(rows)}</div></div></section>'
    )


def crumbs(root, fm):
    if not fm["path"]:
        return ""
    trail = [f'<a href="{root}">Home</a>']
    for name, p in fm.get("parents", []):
        trail.append(f'<a href="{root}{p}">{esc(name)}</a>')
    trail.append(f'<span aria-current="page">{esc(fm["crumb"])}</span>')
    return '<nav class="crumbs" aria-label="Breadcrumb">' + icon("chev-r").join(trail) + "</nav>"


# ---------------------------------------------------------------------------
# JSON-LD

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def business_node():
    return {
        "@type": "ProfessionalService",
        "@id": BASE + "#business",
        "name": site["name"],
        "alternateName": ["Navera", "Navera Digital Marketing Agency"],
        "description": "Navera Marketing is a digital marketing agency in Sonipat, Haryana offering social media management, reels and video production, graphic design and branding, website development, paid advertising on Meta and Google, and SEO with Google Business Profile support.",
        "slogan": site["tagline"],
        "url": BASE,
        "logo": {"@type": "ImageObject", "url": BASE + "assets/img/logo-512.png", "width": 512, "height": 512},
        "image": BASE + "assets/img/og/home.jpg",
        "telephone": site["phones"][0]["e164"],
        "contactPoint": [
            {"@type": "ContactPoint", "telephone": p["e164"], "contactType": "sales", "areaServed": "IN", "availableLanguage": ["en", "hi"]}
            for p in site["phones"]
        ],
        "address": {"@type": "PostalAddress", "addressLocality": "Sonipat", "addressRegion": "Haryana", "addressCountry": "IN"},
        "areaServed": [{"@type": "City", "name": "Sonipat"}] + [{"@type": "Place", "name": a + ", Sonipat, Haryana"} for a in AREAS[1:]] + [{"@type": "AdministrativeArea", "name": "Sonipat district, Haryana"}],
        "sameAs": [site["instagram"]],
        "knowsAbout": ["Digital marketing", "Social media management", "Instagram marketing", "Reels", "Video production", "Graphic design", "Branding", "Website development", "E-commerce websites", "Google Ads", "Meta Ads", "Local SEO", "Google Business Profile"],
        "priceRange": "₹6,999 - ₹29,999",
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Digital marketing services in Sonipat",
            "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n + " in Sonipat", "url": BASE + p}} for p, n, *_ in SERVICES
            ] + [
                {"@type": "Offer", "name": n + " plan", "description": d, "url": BASE + "pricing/",
                 "price": str(pr), "priceCurrency": "INR",
                 "priceSpecification": {"@type": "UnitPriceSpecification", "price": str(pr), "priceCurrency": "INR", "unitText": "MONTH", "valueAddedTaxIncluded": False},
                 "itemOffered": {"@type": "Service", "name": "Social media & content plan: " + n}}
                for n, pr, d in PLANS
            ] + [
                {"@type": "Offer", "name": n, "description": d, "url": BASE + "website-designing-company-sonipat/",
                 "price": str(pr), "priceCurrency": "INR",
                 "itemOffered": {"@type": "Service", "name": n + " design and development"}}
                for n, pr, d in WEB_PLANS
            ],
        },
    }


def jsonld(fm, url):
    graph = [business_node()]
    graph.append({
        "@type": "WebSite", "@id": BASE + "#website", "url": BASE, "name": site["name"],
        "alternateName": "Navera", "inLanguage": "en-IN", "publisher": {"@id": BASE + "#business"},
    })
    page_type = {"home": "WebPage", "about": "AboutPage", "contact": "ContactPage", "areas": "CollectionPage", "work": "CollectionPage"}.get(fm["kind"], "WebPage")
    page = {
        "@type": page_type, "@id": url + "#webpage", "url": url, "name": fm["title"],
        "description": fm["description"], "inLanguage": "en-IN",
        "isPartOf": {"@id": BASE + "#website"}, "about": {"@id": BASE + "#business"},
        "primaryImageOfPage": {"@type": "ImageObject", "url": BASE + "assets/img/og/" + og_slug(fm["path"]) + ".jpg"},
    }
    if fm["path"]:
        crumbs_ = [("Home", BASE)] + [(n, BASE + p) for n, p in fm.get("parents", [])] + [(fm["crumb"], url)]
        graph.append({
            "@type": "BreadcrumbList", "@id": url + "#breadcrumb",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs_, 1)],
        })
        page["breadcrumb"] = {"@id": url + "#breadcrumb"}
    graph.append(page)
    if fm["kind"] == "service":
        svc = next(s for s in SERVICES if s[0] == fm["path"])
        graph.append({
            "@type": "Service", "@id": url + "#service", "name": strip_tags(fm["h1"]),
            "serviceType": svc[4], "description": fm["description"], "url": url,
            "provider": {"@id": BASE + "#business"},
            "areaServed": [{"@type": "City", "name": "Sonipat"}] + [{"@type": "Place", "name": a + ", Sonipat, Haryana"} for a in AREAS[1:]],
            "audience": {"@type": "BusinessAudience", "name": "Businesses in Sonipat and nearby"},
        })
        page["mainEntity"] = {"@id": url + "#service"}
    if fm["kind"] == "work":
        graph.append({
            "@type": "ItemList", "@id": url + "#projects", "name": "Websites and web apps by Navera Marketing",
            "numberOfItems": len(PROJECTS),
            "itemListElement": [
                {"@type": "ListItem", "position": i, "item": {
                    "@type": "WebSite", "name": p["name"], "url": p["url"], "description": p["summary"],
                    "image": BASE + "assets/img/work/" + p["slug"] + ".jpg",
                    "creator": {"@id": BASE + "#business"}}}
                for i, p in enumerate(PROJECTS, 1)
            ],
        })
        page["mainEntity"] = {"@id": url + "#projects"}
    if fm.get("faq"):
        graph.append({
            "@type": "FAQPage", "@id": url + "#faq",
            "mainEntity": [{"@type": "Question", "name": strip_tags(q), "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a.replace("\n\n", " "))}} for q, a in fm["faq"]],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# render

def asset_hash(rel):
    return hashlib.md5((SRC / rel).read_bytes()).hexdigest()[:8]


def expand(text, fm, root):
    # partial includes first (may nest once or twice)
    for _ in range(3):
        text = re.sub(r"\{\{part:([\w-]+)\}\}", lambda m: PARTS[m.group(1)], text)
        text = re.sub(r"\{\{art:([\w-]+)\}\}", lambda m: PARTS["art-" + m.group(1)], text)
    reps = {
        "{{root}}": root,
        "{{faq}}": faq_block(fm),
        "{{cta}}": PARTS["cta"],
        "{{crumbs}}": crumbs(root, fm),
        "{{related}}": related(root, fm["path"]),
        "{{services-cards}}": services_cards(root),
        "{{services-menu}}": services_menu(root),
        "{{services-list}}": services_list(root),
        "{{work-cases}}": work_cases(root),
        "{{work-grid}}": work_grid(root),
        "{{work-filters}}": work_filters(),
        "{{work-stats}}": work_stats(),
        "{{work-marquee}}": work_marquee(),
        "{{work-teaser}}": work_teaser(root),
        "{{work-hero}}": work_hero(root),
        "{{work-count}}": str(len(PROJECTS)),
        "{{insta}}": site["instagram"],
        "{{instahandle}}": site["instagramHandle"],
    }
    for _ in range(2):  # blocks above contain placeholders themselves
        for k, v in reps.items():
            text = text.replace(k, v)
        text = re.sub(r"\{\{part:([\w-]+)\}\}", lambda m: PARTS[m.group(1)], text)
    text = re.sub(r"\{\{icon:([\w-]+)\}\}", lambda m: icon(m.group(1)), text)
    text = re.sub(r"\{\{wa:(\d)\}\}", lambda m: esc(wa_link(int(m.group(1)), fm.get("waText"))), text)
    text = re.sub(r"\{\{wamsg:(\d)\|([^}]*)\}\}", lambda m: esc(wa_link(int(m.group(1)), html.unescape(m.group(2)))), text)
    text = re.sub(r"\{\{waraw:(\d)\}\}", lambda m: site["phones"][int(m.group(1))]["wa"], text)
    text = re.sub(r"\{\{tel:(\d)\}\}", lambda m: site["phones"][int(m.group(1))]["e164"], text)
    text = re.sub(r"\{\{ph:(\d)\}\}", lambda m: site["phones"][int(m.group(1))]["label"], text)
    text = re.sub(r"\{\{cur:([^}]*)\}\}", lambda m: ' aria-current="page"' if m.group(1) == fm["path"] else "", text)
    return text


def head(fm, url, root):
    title, desc = fm["title"], fm["description"]
    robots = "noindex, follow" if fm.get("noindex") else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
    og = BASE + "assets/img/og/" + og_slug(fm["path"]) + ".jpg"
    og_alt = fm.get("ogAlt", strip_tags(fm["h1"]) + " - Navera Marketing, Sonipat")
    css_v, js_v = asset_hash("assets/css/style.css"), asset_hash("assets/js/site.js")
    ga = ""
    if site.get("ga4Id"):
        g = site["ga4Id"]
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script>'
              f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{g}');</script>")
    canonical = "" if fm.get("noindex") else f'<link rel="canonical" href="{url}">\n'
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{canonical}<meta name="robots" content="{robots}">
<meta name="theme-color" content="{site['themeColor']}">
<meta name="author" content="Navera Marketing">
<meta name="geo.region" content="IN-HR">
<meta name="geo.placename" content="Sonipat, Haryana">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Navera Marketing">
<meta property="og:title" content="{esc(fm.get('ogTitle', title))}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(og_alt)}">
<meta property="og:locale" content="en_IN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(fm.get('ogTitle', title))}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og}">
<link rel="icon" href="{root}assets/img/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{root}assets/img/icon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="manifest" href="{root}site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..700;1,6..96,400..700&family=Jost:wght@300..600&display=swap">
<link rel="stylesheet" href="{root}assets/css/style.css?v={css_v}">
<script>document.documentElement.classList.add('js')</script>
<script type="application/ld+json">
{jsonld(fm, url)}
</script>
{ga}</head>
"""


def parse_page(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--page\s*(\{.*?\})\s*-->", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: missing <!--page {{...}} --> front matter")
    fm = json.loads(m.group(1))
    fm.setdefault("kind", "page")
    body = raw[m.end():]
    h = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    fm["h1"] = re.sub(r"\s+", " ", strip_tags(h.group(1))) if h else fm["title"]
    return fm, body


def render(fm, body):
    path = fm["path"]
    url = BASE + path if path != "404.html" else BASE + "404.html"
    root = rel_prefix(path) if path != "404.html" else ""
    if path == "404.html":
        root = "/" + BASE.split("/", 3)[3] if BASE.count("/") > 3 else "/"
    page = head(fm, url, root)
    page += f'<body class="page-{fm["kind"]}">\n<a class="skip" href="#main">Skip to content</a>\n'
    page += PARTS["icons"] + PARTS["header"] + f'<main id="main">\n{body}\n</main>\n' + PARTS["footer"]
    page += f'<script src="{root}assets/js/site.js?v={asset_hash("assets/js/site.js")}" defer></script>\n</body>\n</html>\n'
    return expand(page, fm, root)


# ---------------------------------------------------------------------------
# site files

def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def site_files(pages):
    idx = [fm for fm, _ in pages if not fm.get("noindex")]
    urls = "".join(
        f"  <url><loc>{BASE + fm['path']}</loc><lastmod>{site['lastmod']}</lastmod>"
        f"<changefreq>{'weekly' if not fm['path'] else 'monthly'}</changefreq><priority>{fm.get('priority', '0.8')}</priority></url>\n"
        for fm in idx
    )
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    write(".nojekyll", "")
    if site.get("customDomain"):
        write("CNAME", site["customDomain"].strip("/") + "\n")
    manifest = {
        "name": "Navera Marketing", "short_name": "Navera", "start_url": "./", "display": "standalone",
        "background_color": "#0c0408", "theme_color": site["themeColor"],
        "icons": [{"src": "assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "assets/img/logo-512.png", "sizes": "512x512", "type": "image/png"}],
    }
    write("site.webmanifest", json.dumps(manifest, indent=1))
    phones = ", ".join("+91 " + p["label"] for p in site["phones"])
    lines = [
        "# Navera Marketing",
        "",
        "> Navera Marketing is a digital marketing agency based in Sonipat, Haryana, India. "
        "Tagline: \"A New Era of Brand Growth\". Services: social media management (Instagram, Facebook), "
        "reels and video production with on-location shoots, graphic design and branding, website development "
        "(basic, catalogue and e-commerce), paid advertising on Meta and Google, and SEO with Google Business Profile support.",
        "",
        "- All prices are negotiable.",
        "- Monthly plans (service fee, GST extra if applicable, ad spend separate): Essential Rs 9,999/month (10 reels, 10 stories, 2 shoots); "
        "Business Growth Rs 19,999/month (16 reels, 16 stories, 8 graphics, 4 shoots, Google Business Profile support); "
        "Premium Growth Rs 24,999/month (reels as required, 20 stories, 12 graphics, basic SEO, campaign coordination).",
        "- Websites (one-time): Basic Rs 6,999; Catalogue Rs 14,999 (hosting included); E-commerce Rs 29,999 (hosting + domain included).",
        "",
        f"- Location: Sonipat, Haryana, India. Serves Sonipat city and Sonipat district ({', '.join(AREAS[1:])}) and works online with brands across India.",
        f"- Contact (WhatsApp and phone): {phones}",
        f"- Instagram: {site['instagram']}",
        "",
        "## Portfolio (websites and web apps built by Navera Marketing)",
        "",
    ] + [
        f"- [{p['name']}]({p['url']}) ({KIND_LABEL[p['kind']].lower()}; {', '.join(x for x in (p['industry'], p.get('city')) if x)}): {p['summary']}"
        for p in PROJECTS
    ] + [
        "",
        "## Pages",
        "",
    ]
    for fm in idx:
        lines.append(f"- [{fm['title']}]({BASE + fm['path']}): {fm['description']}")
    write("llms.txt", "\n".join(lines) + "\n")


def copy_assets():
    dst = OUT / "assets"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC / "assets", dst)


# ---------------------------------------------------------------------------
# audit

def audit(pages):
    problems = []
    for fm, _ in pages:
        rel = fm["path"] + ("index.html" if not fm["path"].endswith(".html") else "")
        f = OUT / rel
        t = f.read_text(encoding="utf-8")
        name = rel
        if "{{" in t:
            problems.append(f"{name}: unreplaced placeholder {re.search(r'{{[^}]*}}', t).group(0)}")
        if len(re.findall(r"<h1[\s>]", t)) != 1:
            problems.append(f"{name}: expected exactly one <h1>")
        title = re.search(r"<title>(.*?)</title>", t).group(1)
        desc = re.search(r'<meta name="description" content="(.*?)">', t).group(1)
        if not fm.get("noindex"):
            if len(html.unescape(title)) > 62:
                problems.append(f"{name}: title {len(html.unescape(title))} chars")
            dl = len(html.unescape(desc))
            if not 120 <= dl <= 160:
                problems.append(f"{name}: description {dl} chars")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
            try:
                json.loads(block)
            except Exception as e:  # noqa
                problems.append(f"{name}: JSON-LD invalid: {e}")
        ids = re.findall(r'\sid="([^"]+)"', t)
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            problems.append(f"{name}: duplicate ids {sorted(dup)}")
        # internal links
        if fm["path"] != "404.html":
            for href in re.findall(r'(?:href|src)="([^"#]+)', t):
                if re.match(r"(https?:|mailto:|tel:|data:|//)", href):
                    continue
                target = (f.parent / urllib.parse.unquote(href.split("?")[0])).resolve()
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    problems.append(f"{name}: broken link {href}")
        for href in re.findall(r'<use href="#([^"]+)"', t):
            if f'id="{href}"' not in t:
                problems.append(f"{name}: missing symbol #{href}")
    return problems


# ---------------------------------------------------------------------------
# images (favicons + share cards) via headless Chrome

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def chrome_shot(html_path, png_path, w, h, transparent=False):
    chrome = next((p for p in CHROME_PATHS if pathlib.Path(p).exists()), None)
    if not chrome:
        raise SystemExit("Chrome/Edge not found")
    prof = TOOLS / ".cache" / "chrome-profile"
    args = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--user-data-dir={prof}", f"--window-size={w},{h}",
            "--virtual-time-budget=8000", f"--screenshot={png_path}"]
    if transparent:
        args.append("--default-background-color=00000000")
    args.append(pathlib.Path(html_path).resolve().as_uri())
    if pathlib.Path(png_path).exists():
        pathlib.Path(png_path).unlink()
    subprocess.run(args, check=False, capture_output=True, timeout=120)
    if not pathlib.Path(png_path).exists():
        raise SystemExit(f"screenshot failed: {html_path}")


def png_to(src, dst, w, h, fmt="jpg", quality=84):
    ps = TOOLS / "resize.ps1"
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps),
                    "-In", str(src), "-Out", str(dst), "-W", str(w), "-H", str(h), "-Format", fmt, "-Quality", str(quality)],
                   check=True)


def make_images(pages):
    cache = TOOLS / ".cache"
    cache.mkdir(exist_ok=True)
    img = SRC / "assets" / "img"
    (img / "og").mkdir(parents=True, exist_ok=True)
    tpl_icon = (TOOLS / "icon-template.html").read_text(encoding="utf-8")
    p = cache / "icon.html"
    p.write_text(tpl_icon, encoding="utf-8")
    chrome_shot(p, cache / "icon.png", 512, 512)
    shutil.copy(cache / "icon.png", img / "logo-512.png")
    png_to(cache / "icon.png", img / "icon-192.png", 192, 192, "png")
    png_to(cache / "icon.png", img / "apple-touch-icon.png", 180, 180, "png")
    tpl = (TOOLS / "og-template.html").read_text(encoding="utf-8")
    for fm, _ in pages:
        if fm.get("noindex"):
            continue
        slug = og_slug(fm["path"])
        head_html = fm.get("ogHeadline") or esc(fm["h1"])
        kicker = fm.get("ogKicker", "Digital Marketing Agency in Sonipat")
        h = tpl.replace("{{headline}}", head_html).replace("{{kicker}}", esc(kicker)) \
               .replace("{{phone}}", site["phones"][0]["label"])
        hp = cache / f"og-{slug}.html"
        hp.write_text(h, encoding="utf-8")
        chrome_shot(hp, cache / f"og-{slug}.png", 1200, 630)
        png_to(cache / f"og-{slug}.png", img / "og" / f"{slug}.jpg", 1200, 630, "jpg", 86)
        print("og:", slug)


# ---------------------------------------------------------------------------

def main():
    pages = [parse_page(p) for p in sorted((SRC / "pages").glob("*.html"))]
    if "--images" in sys.argv:
        make_images(pages)
    if OUT.exists():
        for child in OUT.iterdir():
            if child.name == "CNAME" or (child.name.startswith("google") and child.name.endswith(".html")):  # keep CNAME + Search Console verification file
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    OUT.mkdir(exist_ok=True)
    copy_assets()
    for fm, body in pages:
        rel = fm["path"] + ("index.html" if not fm["path"].endswith(".html") else "")
        write(rel, render(fm, body))
    site_files(pages)
    problems = audit(pages)
    print(f"built {len(pages)} pages -> {OUT}  (base {BASE})")
    if problems:
        print("AUDIT ISSUES:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("audit: OK")


if __name__ == "__main__":
    main()
