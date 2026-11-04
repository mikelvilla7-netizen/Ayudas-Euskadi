#!/usr/bin/env python3
"""Descarga las ayudas del Gobierno Vasco (Open Data Euskadi), las limpia y escribe docs/data.json.
Solo usa la librería estándar. Fuente: licencia CC BY 4.0."""
import json, os, re, sys, urllib.request
from datetime import date, datetime, timezone

SOURCE = os.environ.get(
    "SOURCE_URL",
    "https://opendata.euskadi.eus/contenidos/ds_ayudas_subvenciones/ultimas_ayudas_subvencion_bec/opendata/ayudas.json",
)
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data.json")

# Orden importa: la primera regla que coincida con el título gana.
TITLE_RULES = [
    ("Vivienda y energía", r"alquiler|vivienda|rehabilitaci|energ|alojamiento"),
    ("Familias y educación", r"euskera|euskaltegi|beca|estudi|educaci|alumnado|familia|hijas|escolar|juventud"),
    ("Agro y pesca", r"agr[ií]|agrari|pesca|ganad|acuicultura|fempa"),
    ("Empleo y formación", r"empleo|formaci|hezibi|pr[aá]ctic|discapacidad|lanbide"),
    ("Empresa y emprendimiento", r"emprend|empresa|econom[ií]a social|aut[oó]nom|competencia|compliance|industri"),
    ("Medio ambiente y transporte", r"transporte|medio ambiente|renaturaliz|biodivers|clim[aá]tic|protecci[oó]n civil|contaminaci|residuos"),
    ("Salud y bienestar", r"sanitari|tratamiento|salud|v[ií]ctima|humanitari|psicol[oó]gic|dependencia|inclusi[oó]n social|exclusi[oó]n"),
    ("Cultura", r"cultura|zinema|literatura|cine\b|m[uú]sica|teatro|videojuego|audiovisual|danza|museo|patrimonio|libro"),
    ("Investigación e innovación", r"investigad|horizon|i\+d|marie|ciencia|innovaci|tecnolog|doctor"),
]
DEPT_RULES = [
    ("Vivienda y energía", r"vivienda|energ"),
    ("Familias y educación", r"educaci|habe|bienestar|juventud"),
    ("Agro y pesca", r"alimentaci|agricultura|pesca"),
    ("Empleo y formación", r"lanbide|osalan"),
    ("Empresa y emprendimiento", r"econom|industria|competencia|turismo"),
    ("Cultura", r"cultura"),
    ("Salud y bienestar", r"salud|derechos humanos|convivencia"),
    ("Medio ambiente y transporte", r"medio ambiente|movilidad|transporte|sostenib"),
]

def classify(title, dept):
    t, d = title.lower(), dept.lower()
    for area, rx in TITLE_RULES:
        if re.search(rx, t):
            return area
    for area, rx in DEPT_RULES:
        if re.search(rx, d):
            return area
    return "Otras"

def difficulty(title):
    """Estimación por palabras clave (el feed no la trae). Se corrige con overrides.json."""
    t = title.lower()
    if re.search(r"horizon|feder|convocatoria de propuestas|internacionalizaci|i\+d|programa marco|rehabilitaci[oó]n integral|obras|promoci[oó]n|constituci[oó]n|pr[eé]stamo|fondo perdido|auditor|fempa|inversi|alojamientos|arrendamiento", t):
        return "compleja"
    if re.search(r"mensual|estudiante|beca|euskera|pr[aá]ctica|bono|cheque|premio|adherencia", t):
        return "facil"
    return "media"

def profile(title, org):
    t = (title + " " + org).lower()
    if re.search(r"administraci[oó]n local|ayuntamiento|asociativ|confederaci|entidades|comunitaria|investigad|humanitari|renaturaliz|protecci[oó]n civil|horizon", t):
        return "Entidades"
    if re.search(r"empresa|emprend|aut[oó]nom|econom[ií]a social|compliance|competencia|hezibi|fempa|pesca|agr[ií]", t):
        return "Empresas"
    if re.search(r"familia|estudiante|vivienda|alquiler|euskera|hijas|adquisici|v[ií]ctima|adherencia|tratamiento|sanitari", t):
        return "Particulares"
    return "Todos"

def load_overrides():
    path = os.path.join(os.path.dirname(__file__), "..", "overrides.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def parse(d):
    try:
        return datetime.strptime(d, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None

def load(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    raw = load(SOURCE)
    today, out, seen = date.today(), [], set()
    overrides = load_overrides()
    for x in raw:
        title = (x.get("documentName") or "").strip()
        if not title or x.get("procedureHistorical") == "Sí" or x.get("procedureStatus") == "Histórico":
            continue
        end, start = parse(x.get("procedureEndDate")), parse(x.get("procedureStartDate"))
        if end is None or end < today:
            continue
        # Convocatorias antiguas con fecha de cierre falsa (2035+) o con un año pasado en el título
        if end.year >= 2035 and start and start.year < today.year - 2:
            continue
        yrs = [int(y) for y in re.findall(r"(?<![/\d])(20\d{2})\b", title)]
        if yrs and (max(yrs) < today.year - 1 or (max(yrs) < today.year and end.year >= today.year + 2)):
            continue
        url = x.get("friendlyUrl") or x.get("physicalUrl")
        if not url or url in seen:
            continue
        seen.add(url)
        dept = x.get("department") or x.get("institution") or ""
        org = dept.split("#")[0].strip() or x.get("procedureCollection", "")
        full = title
        if len(title) > 140:
            title = title[:140].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        item = {
            "title": title,
            "org": org,
            "area": classify(title, dept),
            "dificultad": difficulty(title),
            "perfil": profile(title, org),
            "start": start.isoformat() if start else None,
            # Fechas de 2035+ son "indefinido" en la práctica
            "end": None if end.year >= 2035 else end.isoformat(),
            "url": url,
        }
        if full != title:
            item["resumen"] = full
            item["title_full"] = full
        # Capa editorial: overrides.json {"trozo de url o título": {"dificultad","perfil","resumen","importe"}}
        for key, extra in overrides.items():
            if key.lower() in (url + " " + full).lower():
                item.update(extra)
        out.append(item)
    out.sort(key=lambda a: (a["end"] is None, a["end"] or ""))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "source": "Open Data Euskadi (CC BY 4.0)", "items": out},
                  f, ensure_ascii=False, indent=1)
    print(f"{len(out)} ayudas abiertas de {len(raw)} registros -> data.json")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
