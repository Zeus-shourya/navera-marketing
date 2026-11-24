# Navera Marketing website

Website for **Navera Marketing**, a digital marketing agency in Sonipat (Instagram: @navera.marketing).
Theme taken from the Instagram page: black-plum and wine silk, orchid glow, lavender band, champagne "chrome" type
(Bodoni Moda + Jost). Services, plans and prices come from `Navera_Marketing_Proposal_2026_Revised_3.pdf`.

## Work on it

```
py tools\build.py            # build src\ -> docs\ and run the SEO / link audit
py tools\build.py --images   # also re-render favicons + share images (needs Chrome + internet)
powershell -ExecutionPolicy Bypass -File serve.ps1    # preview at http://localhost:4461/
```

- `src\site.json`: name, phones (WhatsApp), Instagram, base URL / custom domain, GA4 id, lastmod date.
- `src\pages\*.html`: one file per page. The JSON comment at the top holds title, description and FAQ
  (the FAQ is rendered on the page *and* as FAQPage schema from the same text).
- `src\partials\`: header, footer, WhatsApp panel, CTA, process steps, and the SVG illustrations (`art-*.html`).
- `src\assets\css\style.css`, `src\assets\js\site.js`: design system and behaviour.
- `tools\build.py`: also holds the service list, plan prices (`PLANS`, `WEB_PLANS`) used in schema and llms.txt.
  If prices change, update them there **and** in `pricing.html`, `index.html`, the service pages and the FAQ.

## Portfolio (`/work/`)

- `src\work.json` lists every project (name, live URL, kind, industry, city, filter categories, summary, tags).
  `featured: true` projects become the big case studies at the top of `/work/` and the 3 cards on the home page.
- Screenshots live in `src\assets\img\work\` (`<slug>.jpg`, `<slug>-sm.jpg`, `<slug>-m.jpg`). To add or refresh one:

```
py tools\shots.py <slug>      # captures the live site, desktop + phone (needs Chrome + internet)
py tools\build.py
```

- Stats on `/work/` (projects, clients, own domains) are counted from `work.json`, so they stay correct when you add a project.

## SEO built in

| Page | Target searches |
| --- | --- |
| `/` | digital marketing agency / company in Sonipat, best digital marketing agency in Sonipat, marketing agency in Sonipat |
| `/social-media-marketing-sonipat/` | social media marketing agency Sonipat, Instagram management |
| `/video-production-sonipat/` | reels shoot / video production Sonipat |
| `/graphic-design-branding-sonipat/` | graphic designer in Sonipat, branding |
| `/website-designing-company-sonipat/` | website designing company in Sonipat, website design price |
| `/google-ads-meta-ads-sonipat/` | advertising agency in Sonipat, Google / Meta ads |
| `/seo-company-sonipat/` | SEO company / services / expert in Sonipat, Google Business Profile |
| `/pricing/` | digital marketing packages / cost in Sonipat |
| `/areas-we-serve/` | digital marketing in Kundli, Ganaur, Gohana, Murthal, Rai, Kharkhoda |

Every page: unique title + description, canonical, Open Graph / WhatsApp share image, JSON-LD
(ProfessionalService with real plan prices, Service, BreadcrumbList, FAQPage), sitemap.xml, robots.txt and llms.txt
(for AI assistants). No fake reviews, ratings, addresses or client counts.

## To actually rank #1 in Sonipat (outside this code)

1. **Google Business Profile** (biggest factor for "near me" and map results): create/verify "Navera Marketing",
   category *Marketing agency* (+ *Internet marketing service*, *Website designer*, *Advertising agency*), add the
   website link, all services, photos and weekly posts, and ask every happy client for a Google review.
2. **Domain**: buy one (e.g. naveramarketing.com / navera.in), put it in `customDomain` in `src\site.json`, rebuild.
3. **Search Console**: verify the site and submit `sitemap.xml`.
4. Put the website link in the Instagram bio, and list the business on Justdial / IndiaMART with the same name and phone.
5. Missing details to add when available: office address, email, opening hours, real client work and reviews.
