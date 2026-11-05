#!/usr/bin/env python3
"""Genera, a partir de docs/data.json: una página estática por ayuda (castellano y euskera),
sitemap.xml, robots.txt, feed.xml / feed-eu.xml, y las etiquetas SEO de docs/index.html.
Solo usa la librería estándar.

URL pública: variable SITE_URL, o "url" de site.json, o (en GitHub Actions) se deduce de
GITHUB_REPOSITORY como https://USUARIO.github.io/REPO. Analítica opcional: GOATCOUNTER o
"goatcounter" de site.json (código de tu cuenta de goatcounter.com, sin cookies).
"""
import hashlib, html, json, os, re, shutil, unicodedata
from datetime import date, datetime, timezone
from email.utils import format_datetime

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.path.join(ROOT, "docs")
NAME = "Laguntzak · Ayudas Euskadi"
E = html.escape

def read_cfg():
    try:
        with open(os.path.join(ROOT, "site.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

CFG = read_cfg()
BASE = (os.environ.get("SITE_URL") or CFG.get("url") or "").rstrip("/")
if not BASE and os.environ.get("GITHUB_REPOSITORY"):
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    BASE = f"https://{owner}.github.io/{repo}"
GC = os.environ.get("GOATCOUNTER") or CFG.get("goatcounter") or ""
ANALYTICS = (f'<script data-goatcounter="https://{E(GC)}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>' if GC else "")
GSC = os.environ.get("GOOGLE_VERIFICATION") or CFG.get("google_verification") or ""
GSC_META = f'<meta name="google-site-verification" content="{E(GSC)}">' if GSC else ""
OWNER = CFG.get("owner") or {}
HOSTING = CFG.get("hosting") or "GitHub Pages (GitHub, Inc.)"
THEME_JS = "try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}"
MISSING = set()
TODAY = date.today()

AREAS = {  # nombre en datos -> (icono, castellano, euskera)
    "Vivienda y energía": ("🏠", "Vivienda y energía", "Etxebizitza eta energia"),
    "Familias y educación": ("🎓", "Familias y educación", "Familiak eta hezkuntza"),
    "Agro y pesca": ("🌾", "Agro y pesca", "Nekazaritza eta arrantza"),
    "Empleo y formación": ("💼", "Empleo y formación", "Enplegua eta prestakuntza"),
    "Empresa y emprendimiento": ("🚀", "Empresa y emprendimiento", "Enpresa eta ekintzailetza"),
    "Medio ambiente y transporte": ("🌿", "Medio ambiente y transporte", "Ingurumena eta garraioa"),
    "Salud y bienestar": ("🩺", "Salud y bienestar", "Osasuna eta ongizatea"),
    "Cultura": ("🎭", "Cultura", "Kultura"),
    "Investigación e innovación": ("🔬", "Investigación e innovación", "Ikerketa eta berrikuntza"),
    "Otras": ("📄", "Otras", "Besteak"),
}
TX = {
 "es": dict(back="← Todas las ayudas", until="Plazo hasta el", nolimit="Sin fecha límite definida", amount="Importe",
   keys="Requisitos clave", src="Fuente", official="Ver convocatoria oficial →", related="Ayudas relacionadas",
   disc="Información orientativa elaborada a partir de datos abiertos del Gobierno Vasco (CC BY 4.0). Consulta siempre la convocatoria oficial antes de solicitar.",
   auto="", other="Euskaraz", diff={"facil": "Dificultad: fácil", "media": "Dificultad: media", "compleja": "Dificultad: compleja"},
   prof={"Particulares": "Para particulares", "Empresas": "Para empresas", "Entidades": "Para entidades", "Todos": "Para todos"},
   rss="Suscríbete por RSS", home="Ayudas abiertas en Euskadi", desc_t="Ayuda de {org}: {title}. {plazo}"),
 "eu": dict(back="← Laguntza guztiak", until="Epemuga:", nolimit="Epemugarik gabe", amount="Zenbatekoa",
   keys="Baldintza nagusiak", src="Iturria", official="Ikusi deialdi ofiziala →", related="Erlazionatutako laguntzak",
   disc="Informazio orientagarria, Eusko Jaurlaritzaren datu irekietatik (CC BY 4.0) eginda. Eskatu aurretik, kontsultatu beti deialdi ofiziala.",
   auto="Itzulpen automatikoa", other="En castellano", diff={"facil": "Zailtasuna: erraza", "media": "Zailtasuna: ertaina", "compleja": "Zailtasuna: konplexua"},
   prof={"Particulares": "Partikularrentzat", "Empresas": "Enpresentzat", "Entidades": "Erakundeentzat", "Todos": "Guztientzat"},
   rss="Harpidetu RSS bidez", home="Euskadiko laguntza irekiak", desc_t="{org}(r)en laguntza: {title}. {plazo}"),
}

def slugify(title, url):
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60].rstrip("-")
    return f"{s or 'ayuda'}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"

def cut(t, n):
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(".,;:(") + "…"

def fmt(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")

CSS = """:root{--bg:#f6f3ee;--fg:#1f1d1a;--muted:#6b665e;--card:#fff;--line:#e6e0d6;--chip:#ebe5d9;--accent:#1f1d1a;--on:#fff;--brand:#2e7d4f;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141311;--fg:#f0ece4;--muted:#a09a8f;--card:#1e1c19;--line:#34312c;--chip:#2a2723;--accent:#f0ece4;--on:#141311;--brand:#81c784;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141311;--fg:#f0ece4;--muted:#a09a8f;--card:#1e1c19;--line:#34312c;--chip:#2a2723;--accent:#f0ece4;--on:#141311;--brand:#81c784;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:720px;margin:0 auto;padding:20px 16px 40px}a{color:var(--brand)}
.back{display:inline-block;margin-bottom:14px;font-size:.9rem;text-decoration:none;font-weight:600}
.kick{color:var(--brand);font-weight:700;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:1.7rem;line-height:1.2;margin:6px 0}.org{color:var(--muted);font-size:.9rem}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.chips span{background:var(--chip);border-radius:999px;padding:5px 12px;font-size:.85rem}
.box{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:16px 0}.box h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 6px}
ul{margin:6px 0 0;padding-left:20px}li{margin:5px 0}.src,.disc,footer{color:var(--muted);font-size:.8rem}
.btn{display:inline-block;background:var(--accent);color:var(--on);text-decoration:none;font-weight:700;padding:11px 18px;border-radius:12px;margin:10px 0}
.rel a{display:block;padding:8px 0;border-top:1px solid var(--line);text-decoration:none;color:inherit;font-size:.95rem}.rel a:first-of-type{border-top:0}
footer{margin-top:28px;display:flex;gap:16px;flex-wrap:wrap}"""

def page(x, lang, items_by_area, slug_by_url):
    t = TX[lang]
    eu = lang == "eu"
    title = (x.get("title_eu") if eu else None) or x["title"]
    org = (x.get("org_eu") if eu else None) or x.get("org", "")
    full = (x.get("title_full") if not eu else None) or title
    ic, an_es, an_eu = AREAS.get(x["area"], AREAS["Otras"])
    area = an_eu if eu else an_es
    resumen = (x.get("resumen_eu") if eu else x.get("resumen")) or (x.get("resumen_eu") if eu else None)
    importe = (x.get("importe_eu") if eu else x.get("importe"))
    claves = (x.get("claves_eu") if eu else x.get("claves")) or []
    plazo = f'{t["until"]} {fmt(x["end"])}' if x.get("end") else t["nolimit"]
    desc = cut(resumen or t["desc_t"].format(org=org, title=title, plazo=plazo), 155)
    rel_path = "../" if lang == "es" else "../../"
    home = rel_path + "index.html"
    own = f'{BASE}/{"eu/" if eu else ""}ayuda/{x["slug"]}.html' if BASE else ""
    seo = ""
    if BASE:
        es_u, eu_u = f'{BASE}/ayuda/{x["slug"]}.html', f'{BASE}/eu/ayuda/{x["slug"]}.html'
        seo = (f'<link rel="canonical" href="{E(own)}">'
               + (f'<link rel="alternate" hreflang="es" href="{E(es_u)}">' + (f'<link rel="alternate" hreflang="eu" href="{E(eu_u)}">' if x.get("title_eu") else ""))
               + f'<meta property="og:url" content="{E(own)}">')
    ld = {"@context": "https://schema.org", "@type": "GovernmentService", "name": title, "description": desc,
          "serviceType": area, "areaServed": "Euskadi", "inLanguage": lang, "url": x["url"]}
    if org:
        ld["provider"] = {"@type": "GovernmentOrganization", "name": org}
    ld_s = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    rel = [r for r in items_by_area.get(x["area"], []) if r["slug"] != x["slug"]][:4]
    if eu:
        rel = [r for r in rel if r.get("title_eu")]
    rel_html = "".join(f'<a href="{E(r["slug"])}.html">{E((r.get("title_eu") if eu else None) or r["title"])}</a>' for r in rel)
    alt_href = (f'../../ayuda/{x["slug"]}.html' if eu else f'../eu/ayuda/{x["slug"]}.html')
    alt = f'<a href="{alt_href}" hreflang="{"es" if eu else "eu"}">{t["other"]}</a>' if (eu or x.get("title_eu")) else ""
    feed = f'<a href="{rel_path}feed{"-eu" if eu else ""}.xml">{t["rss"]}</a>'
    lang_js = f"try{{localStorage.setItem('lang','{lang}')}}catch(e){{}}"
    theme_js = "try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}"
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(cut(title, 62))} · {NAME}</title>
<meta name="description" content="{E(desc)}">
{seo}<meta property="og:type" content="article"><meta property="og:title" content="{E(cut(title, 90))}"><meta property="og:description" content="{E(desc)}">
<script type="application/ld+json">{ld_s}</script>
<style>{CSS}</style><script>{theme_js};{lang_js}</script>{ANALYTICS}{GSC_META}</head>
<body><main>
<a class="back" href="{home}">{t["back"]}</a>
<article>
<div class="kick">{ic} {E(area)}</div>
<h1>{E(title)}</h1>
<div class="org">{E(org)}</div>
<div class="chips"><span>⏰ {E(plazo)}</span><span>{E(t["diff"].get(x.get("dificultad"), t["diff"]["media"]))}</span><span>{E(t["prof"].get(x.get("perfil"), t["prof"]["Todos"]))}</span></div>
{f'<p>{E(resumen)}</p>' if resumen else (f'<p>{E(full)}</p>' if full != title else '')}
{f'<div class="box"><h2>{t["amount"]}</h2>{E(importe)}</div>' if importe else ''}
{f'<div class="box"><h2>{t["keys"]}</h2><ul>' + "".join(f"<li>{E(c)}</li>" for c in claves) + '</ul>' + (f'<div class="src">{t["src"]}: {E(x["fuente"])}</div>' if x.get("fuente") else '') + '</div>' if claves else ''}
<a class="btn" href="{E(x["url"])}" target="_blank" rel="noopener noreferrer">{t["official"]}</a>
{f'<div class="src">{t["auto"]}</div>' if eu and x.get("eu_auto") and not claves else ''}
<p class="disc">{t["disc"]}</p>
</article>
{f'<section class="box rel"><h2>{t["related"]}</h2>{rel_html}</section>' if rel_html else ''}
<footer>{alt}{feed}<a href="{home}">{t["home"]}</a>{legal_links(lang, rel_path)}</footer>
</main></body></html>"""

def fld(key, label, required=True):
    v = str(OWNER.get(key) or "").strip()
    if v:
        return E(v)
    if required:
        MISSING.add(label)
        return f'<mark>[COMPLETAR: {E(label)}]</mark>'
    return ""

def mail():
    v = str(OWNER.get("email") or "").strip()
    if v:
        return f'<a href="mailto:{E(v)}">{E(v)}</a>'
    MISSING.add("correo electrónico")
    return '<mark>[COMPLETAR: correo electrónico]</mark>'

def legal_links(lang, prefix):
    L = {"es": ("Sobre este proyecto", "Aviso legal", "Privacidad", "Cookies"),
         "eu": ("Proiektuari buruz", "Lege-oharra (es)", "Pribatutasuna (es)", "Cookieak (es)")}[lang]
    about = f"{prefix}{'eu/' if lang == 'eu' else ''}sobre.html"
    return (f'<a href="{about}">{L[0]}</a><a href="{prefix}aviso-legal.html">{L[1]}</a>'
            f'<a href="{prefix}privacidad.html">{L[2]}</a><a href="{prefix}cookies.html">{L[3]}</a>')

def doc(title, body, lang, prefix, path):
    canon = f'<link rel="canonical" href="{E(BASE)}/{path}">' if BASE else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · {NAME}</title>{canon}
<style>{CSS}mark{{background:#ffe08a;color:#000;padding:0 4px;border-radius:4px}}h2{{font-size:1.1rem;margin:22px 0 4px}}</style>
<script>{THEME_JS}</script>{ANALYTICS}{GSC_META}</head>
<body><main><a class="back" href="{prefix}index.html">{TX[lang]["back"]}</a>
<article>{body}</article>
<footer>{legal_links(lang, prefix)}</footer></main></body></html>"""

def legal():
    upd = TODAY.strftime("%d/%m/%Y")
    phone = f"<li>Teléfono: {fld('phone', 'teléfono', False)}</li>" if str(OWNER.get("phone") or "").strip() else ""
    ident = (f"<ul><li>Titular: {fld('name', 'nombre o razón social')}</li><li>NIF: {fld('nif', 'NIF')}</li>"
             f"<li>Domicilio: {fld('address', 'domicilio')}</li><li>Correo electrónico: {mail()}</li>{phone}</ul>")
    site = E(BASE + "/") if BASE else "este sitio"
    aviso = f"""<h1>Aviso legal</h1>
<h2>1. Datos identificativos</h2>
<p>En cumplimiento del artículo 10 de la Ley 34/2002, de servicios de la sociedad de la información y de comercio electrónico (LSSI-CE), se informa de que el titular de este sitio web es:</p>{ident}
<h2>2. Objeto del sitio</h2>
<p>{NAME} ({site}) es un sitio web informativo que reúne y presenta ayudas y subvenciones abiertas en Euskadi a partir de datos abiertos publicados por el Gobierno Vasco. No es un sitio oficial y no está vinculado ni respaldado por el Gobierno Vasco ni por ninguna otra administración.</p>
<h2>3. Condiciones de uso</h2>
<p>El acceso y uso del sitio es gratuito e implica aceptar este aviso. La persona usuaria se compromete a hacer un uso lícito del sitio y a no realizar acciones que puedan dañarlo o dificultar su funcionamiento.</p>
<h2>4. Exclusión de responsabilidad</h2>
<ul><li>La información es orientativa y puede contener errores u omisiones o no estar actualizada. Los plazos, importes y requisitos válidos son los de la convocatoria oficial: consúltala siempre antes de solicitar una ayuda.</li>
<li>Las fichas con «Requisitos clave» se elaboran a partir de fuentes oficiales y pueden quedar desactualizadas con cada convocatoria. La dificultad y la clasificación por temas son estimaciones.</li>
<li>Las traducciones al euskera son automáticas y pueden contener errores.</li>
<li>El sitio enlaza a páginas de terceros sobre cuyo contenido no tiene control ni responsabilidad.</li></ul>
<h2>5. Propiedad intelectual y datos abiertos</h2>
<p>Los datos de las ayudas proceden de Open Data Euskadi (Gobierno Vasco), publicados bajo licencia CC BY 4.0, con atribución a la fuente. El resto de contenidos (fichas, textos y diseño) pertenecen al titular, salvo indicación en contrario. Se permite enlazar a este sitio.</p>
<h2>6. Publicidad y patrocinios</h2>
<p>Este sitio puede incluir publicidad o contenidos patrocinados, que se identificarán claramente como tales.</p>
<h2>7. Legislación aplicable</h2>
<p>Este aviso legal se rige por la legislación española.</p>
<p class="src">Última actualización: {upd}</p>"""
    stats = ("Este sitio usa GoatCounter para obtener estadísticas agregadas de visitas. Según su documentación, no usa cookies ni crea perfiles de personas usuarias individuales."
             if GC else "Actualmente este sitio no utiliza ninguna herramienta de analítica.")
    stats_c = ("Se utiliza GoatCounter para estadísticas agregadas; según su documentación, no usa cookies."
               if GC else "No se utiliza actualmente ninguna herramienta de analítica.")
    priv = f"""<h1>Política de privacidad</h1>
<h2>1. Responsable del tratamiento</h2>{ident}
<h2>2. Qué datos tratamos y para qué</h2>
<ul><li><b>Visitas.</b> {stats}</li>
<li><b>Contacto.</b> Si nos escribes por correo electrónico, usaremos tus datos únicamente para responderte. La base es tu consentimiento al escribirnos y nuestro interés legítimo en atender tu solicitud.</li>
<li><b>Preferencias.</b> El idioma y el tema que eliges se guardan en tu propio navegador y no se envían a ningún servidor.</li></ul>
<h2>3. Servicios de terceros</h2>
<ul><li><b>Alojamiento:</b> {E(HOSTING)}. Recibe tu dirección IP y datos técnicos de la conexión para servir la web.</li>
<li><b>El tiempo:</b> el aviso meteorológico se carga desde tu navegador a Open-Meteo, que recibe tu dirección IP.</li>
<li><b>Enlaces externos:</b> al abrir una convocatoria, pasas a la web de la administración correspondiente, con su propia política.</li></ul>
<h2>4. Conservación, destinatarios y transferencias</h2>
<p>Conservamos los datos de contacto solo el tiempo necesario para atender tu consulta. No cedemos datos a terceros salvo obligación legal. Algunos de los proveedores citados pueden tratar datos fuera del Espacio Económico Europeo con las garantías que establezcan.</p>
<h2>5. Tus derechos</h2>
<p>Puedes ejercer tus derechos de acceso, rectificación, supresión, oposición, limitación y portabilidad escribiendo a {mail()}. Si consideras que no hemos tratado tus datos correctamente, puedes reclamar ante la Agencia Española de Protección de Datos (www.aepd.es).</p>
<p class="src">Última actualización: {upd}</p>"""
    cook = f"""<h1>Política de cookies</h1>
<p>Las cookies son pequeños archivos que un sitio web guarda en tu dispositivo.</p>
<h2>Qué usa este sitio</h2>
<ul><li><b>Cookies propias de seguimiento o publicidad:</b> ninguna.</li>
<li><b>Almacenamiento local del navegador:</b> se usa para recordar el idioma y el tema que eliges. Son preferencias que tú solicitas y no se utilizan para seguirte.</li>
<li><b>Analítica:</b> {stats_c}</li>
<li><b>Terceros:</b> la carga del tiempo (Open-Meteo) y los enlaces a webs oficiales pueden implicar las cookies o registros propios de esos servicios, según sus políticas.</li></ul>
<h2>Cambios futuros</h2>
<p>Si se incorporan publicidad o analítica que use cookies, se pedirá tu consentimiento antes de activarlas y se actualizará esta política.</p>
<h2>Cómo gestionarlas</h2>
<p>Puedes borrar o bloquear cookies y datos del sitio desde la configuración de tu navegador.</p>
<p class="src">Última actualización: {upd}</p>"""
    sobre_es = f"""<h1>Sobre este proyecto</h1>
<p>{NAME} reúne las ayudas y subvenciones abiertas en Euskadi para que sea más fácil saber qué puedes pedir, hasta cuándo y lo complicado que es. No es un sitio oficial ni está vinculado a ninguna administración.</p>
<h2>Cómo se elabora</h2>
<ul><li>Los datos se actualizan cada día de forma automática desde Open Data Euskadi (Gobierno Vasco, licencia CC BY 4.0).</li>
<li>La clasificación por tema, la dificultad y el perfil son automáticas, por lo que pueden fallar.</li>
<li>Las fichas con «Requisitos clave» se han revisado a mano frente a fuentes oficiales.</li>
<li>Las traducciones al euskera son automáticas y están marcadas como tales.</li></ul>
<h2>Limitaciones</h2>
<p>La información es orientativa. Los plazos, importes y requisitos válidos son los de la convocatoria oficial: consúltala siempre antes de solicitar.</p>
<h2>¿Has encontrado un error?</h2>
<p>Escríbenos a {mail()} y lo corregiremos.</p>
<p class="src">Última actualización: {upd}</p>"""
    sobre_eu = f"""<h1>Proiektuari buruz</h1>
<p>{NAME}(e)k Euskadiko laguntza eta diru-laguntza irekiak biltzen ditu, jakiteko errazagoa izan dadin zer eska dezakezun, noizera arte eta zein zaila den. Ez da webgune ofiziala, eta ez dago inongo administraziorekin lotuta.</p>
<h2>Nola egiten da</h2>
<ul><li>Datuak egunero automatikoki eguneratzen dira Open Data Euskadi-tik (Eusko Jaurlaritza, CC BY 4.0 lizentzia).</li>
<li>Gaiaren, zailtasunaren eta hartzaileen araberako sailkapena automatikoa da; beraz, akatsak izan ditzake.</li>
<li>«Baldintza nagusiak» dituzten fitxak eskuz berrikusi dira iturri ofizialen aurka.</li>
<li>Euskarazko itzulpenak automatikoak dira eta horrela markatuta daude.</li></ul>
<h2>Mugak</h2>
<p>Informazioa orientagarria da. Epeak, zenbatekoak eta baldintzak deialdi ofizialean agertzen direnak dira: kontsultatu beti deialdi ofiziala eskatu aurretik.</p>
<h2>Akats bat aurkitu duzu?</h2>
<p>Idatzi iezaguzu {mail()} helbidera eta zuzenduko dugu.</p>
<p class="src">Azken eguneratzea: {upd}</p>"""
    os.makedirs(os.path.join(DOCS, "eu"), exist_ok=True)
    for name, title, body, lang, prefix, path in (
            ("aviso-legal.html", "Aviso legal", aviso, "es", "", "aviso-legal.html"),
            ("privacidad.html", "Política de privacidad", priv, "es", "", "privacidad.html"),
            ("cookies.html", "Política de cookies", cook, "es", "", "cookies.html"),
            ("sobre.html", "Sobre este proyecto", sobre_es, "es", "", "sobre.html"),
            (os.path.join("eu", "sobre.html"), "Proiektuari buruz", sobre_eu, "eu", "../", "eu/sobre.html")):
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as f:
            f.write(doc(title, body, lang, prefix, path))
    if MISSING:
        print("AVISO: faltan datos del titular en las páginas legales: " + ", ".join(sorted(MISSING))
              + ". Complétalos en 'owner' de site.json antes de publicar (aparecen resaltados como [COMPLETAR]).")
    else:
        print("Páginas legales y 'Sobre este proyecto' generadas con los datos del titular")

def rfc(d):
    dt = datetime.strptime(d, "%Y-%m-%d") if d else datetime.combine(TODAY, datetime.min.time())
    return format_datetime(dt.replace(tzinfo=timezone.utc))

def feed(items, lang):
    t = TX[lang]
    eu = lang == "eu"
    rows = sorted(items, key=lambda x: x.get("start") or "", reverse=True)[:30]
    out = []
    for x in rows:
        if eu and not x.get("title_eu"):
            continue
        ttl = (x.get("title_eu") if eu else None) or x["title"]
        link = f'{BASE}/{"eu/" if eu else ""}ayuda/{x["slug"]}.html'
        plazo = f'{t["until"]} {fmt(x["end"])}' if x.get("end") else t["nolimit"]
        d = (x.get("resumen_eu") if eu else x.get("resumen")) or plazo
        out.append(f"<item><title>{E(ttl)}</title><link>{E(link)}</link><guid isPermaLink=\"true\">{E(link)}</guid>"
                   f"<pubDate>{rfc(x.get('start'))}</pubDate><description>{E(d[:300])} ({E(plazo)})</description></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{E(NAME)}</title><link>{E(BASE)}/</link><description>{E(t['home'])}</description><language>{lang}</language>"
            + "".join(out) + "</channel></rss>")

def inject(path, marker, block):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    new = re.sub(rf"<!--{marker}-->.*?<!--/{marker}-->", lambda m: f"<!--{marker}-->{block}<!--/{marker}-->", s, flags=re.S)
    if new != s:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)

def main():
    dpath = os.path.join(DOCS, "data.json")
    with open(dpath, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    changed = False
    for x in items:
        if not x.get("slug"):
            x["slug"] = slugify(x["title_full"] if x.get("title_full") else x["title"], x["url"])
            changed = True
    if changed:
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    for d in ("ayuda", os.path.join("eu", "ayuda")):
        shutil.rmtree(os.path.join(DOCS, d), ignore_errors=True)
        os.makedirs(os.path.join(DOCS, d))
    by_area = {}
    for x in sorted(items, key=lambda i: i.get("end") or "9999"):
        by_area.setdefault(x["area"], []).append(x)
    n_es = n_eu = 0
    for x in items:
        for lang in ("es", "eu"):
            if lang == "eu" and not x.get("title_eu"):
                continue
            sub = "ayuda" if lang == "es" else os.path.join("eu", "ayuda")
            with open(os.path.join(DOCS, sub, x["slug"] + ".html"), "w", encoding="utf-8") as f:
                f.write(page(x, lang, by_area, None))
            n_es += lang == "es"
            n_eu += lang == "eu"
    print(f"{n_es} páginas en castellano y {n_eu} en euskera")
    legal()

    seo = f'<meta name="description" content="{len(items)} ayudas y subvenciones abiertas en Euskadi: plazos, importes y requisitos clave en castellano y euskera.">'
    seo += GSC_META
    if BASE:
        seo += (f'<link rel="canonical" href="{E(BASE)}/"><meta property="og:title" content="{E(NAME)}"><meta property="og:type" content="website">'
                f'<meta property="og:url" content="{E(BASE)}/"><link rel="alternate" type="application/rss+xml" title="RSS" href="{E(BASE)}/feed.xml">')
        urls = [f"{BASE}/", f"{BASE}/sobre.html", f"{BASE}/eu/sobre.html"] + [f"{BASE}/ayuda/{x['slug']}.html" for x in items] + [f"{BASE}/eu/ayuda/{x['slug']}.html" for x in items if x.get("title_eu")]
        sm = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
              + "".join(f"<url><loc>{E(u)}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>" for u in urls) + "</urlset>")
        for name, content in (("sitemap.xml", sm), ("feed.xml", feed(items, "es")), ("feed-eu.xml", feed(items, "eu")),
                              ("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")):
            with open(os.path.join(DOCS, name), "w", encoding="utf-8") as f:
                f.write(content)
        print(f"sitemap.xml ({len(urls)} URLs), feed.xml y robots.txt generados para {BASE}")
    else:
        print("AVISO: sin URL pública no se generan sitemap.xml ni feed.xml. Define SITE_URL o 'url' en site.json "
              "(en GitHub Actions se deduce sola).")
    idx = os.path.join(DOCS, "index.html")
    inject(idx, "SEO", seo)
    inject(idx, "ANALYTICS", ANALYTICS)

if __name__ == "__main__":
    main()
