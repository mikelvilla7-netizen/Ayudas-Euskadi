# Ayudas abiertas en Euskadi

Web estática que lista las ayudas y subvenciones del Gobierno Vasco que siguen abiertas, con datos de
[Open Data Euskadi](https://opendata.euskadi.eus) (licencia CC BY 4.0: hay que citar la fuente).

## Estructura
- `scripts/update_data.py` — descarga el JSON oficial, descarta históricas/cerradas, clasifica por área y escribe `docs/data.json`.
- `docs/index.html` — la web en tarjetas (tema, dificultad estimada, perfil, días restantes); carga `data.json`, sin dependencias.
- `overrides.json` — capa editorial: dificultad, perfil, resumen e importe por ayuda.
- `.github/workflows/update.yml` — ejecuta el script cada día y hace commit si hay cambios.

## Probar en local
```bash
python3 scripts/update_data.py        # genera docs/data.json
python3 -m http.server -d docs 8000   # abre http://localhost:8000
```

## Lanzar (gratis)
1. Sube la carpeta a un repositorio de GitHub.
2. Settings → Pages → Source: *Deploy from a branch*, rama `main`, carpeta `/docs`.
3. Actions → *Actualizar ayudas* → *Run workflow* (la primera vez), y después se actualiza solo.

## Pendiente de analizar
- El feed no trae importes, requisitos ni beneficiarios: hay que añadirlos (a mano en las ayudas clave o leyendo `dataXML` de cada ayuda).
- Solo cubre Gobierno Vasco y UE. Faltan diputaciones forales, ayuntamientos y la BDNS estatal.
- Clasificación, dificultad y perfil se estiman por palabras clave (ver `TITLE_RULES`, `difficulty`, `profile`) y se corrigen en `overrides.json`, donde también puedes añadir resumen e importe por ayuda.
- Fechas basura (cierre 2036+) se tratan como "sin fecha límite".
- Monetización: formulario de contacto para instaladores/gestorías por tema.

## Columnas laterales y monetización
- Izquierda: menú de temas y atajos (cierran esta semana, fáciles).
- Derecha: el tiempo (Open-Meteo, gratis y sin clave; atribución incluida), próximos cierres y un hueco publicitario (`data-slot="side-1"`): pega ahí el código de AdSense o una tarjeta de patrocinador (instaladores, gestorías).
- Para tiempo oficial de Euskalmet haría falta solicitar una clave de API.

## Idioma, tema y cabecera
- **Euskera / castellano:** botón ES | EU arriba a la derecha (se recuerda la elección). Los textos de la interfaz y de las fichas están en `index.html` (objeto `TX`) y en `overrides.json` (`resumen_eu`, `claves_eu`, `importe_eu`). **Las traducciones al euskera son borrador: conviene que las revise una persona euskaldun antes de publicar.**
- **Tema:** botón 🌓 (automático / claro / oscuro), se recuerda la elección.
- **Cabecera rotativa:** por defecto rota 3 ilustraciones (La Concha, Gaztelugatxe, Bilbao). Para usar fotos reales, copia las imágenes en `docs/img/` y crea `docs/hero.json`:
  ```json
  [{"src":"img/concha.jpg","es":"La Concha, Donostia","eu":"Kontxa, Donostia","credit":"Autor · CC BY-SA 4.0"}]
  ```
  Usa solo fotos con licencia libre (p. ej. Wikimedia Commons) o propias, y cita autoría y licencia en `credit`.

## Fichas editoriales (`overrides.json`)
Cada clave es un trozo del título o de la URL de la ayuda. Campos: `dificultad` (facil/media/compleja), `perfil`, `resumen`, `importe`, `claves` (lista), `fuente` y sus versiones `_eu`.
Fichas actuales: vivienda (rehabilitación general, Línea 3 y 4 de fomento del alquiler), economía social (EMIN, EMCP, EMP, asistencia técnica, RSE y participación), HEZIBI-Empresas, empleo de personas con discapacidad, ayudas mensuales a familias (Decreto 87/2026) y euskera (estudiantes y euskaltegis municipales de HABE). Contrastadas con el folleto oficial (Orden de 21/07/2021) y las órdenes de fomento al alquiler; **las cuantías pueden cambiar con cada convocatoria: revisarlas cada año.** Pendiente: auditorías energéticas del EVE, prácticas formativas de Lanbide, formación de delegados de prevención (OSALAN), compliance de competencia y FEMPA. Las fichas con importes de años anteriores lo indican en el texto («en 2024», «en 2025»): confirmar con la convocatoria 2026.

## Traducción automática al euskera
Los títulos y organismos de las ayudas llegan del feed solo en castellano. `scripts/translate_eu.py` los traduce con la API de Claude y guarda cada traducción en `docs/translations_eu.json`, de modo que cada texto se traduce una sola vez (las ayudas nuevas cuestan unos céntimos).
- Necesita una clave de API de Anthropic (console.anthropic.com). En GitHub: Settings → Secrets and variables → Actions → New repository secret, nombre `ANTHROPIC_API_KEY`. Sin clave el sitio sigue funcionando y se muestran los títulos en castellano.
- En local (PowerShell): `$env:ANTHROPIC_API_KEY="tu-clave"; py scripts/translate_eu.py`
- Las ayudas traducidas automáticamente llevan el aviso «Itzulpen automatikoa». Las fichas editoriales (`overrides.json`) no.
- Para corregir una traducción, edita su valor en `docs/translations_eu.json`: la caché tiene prioridad y no se vuelve a traducir.
- Modelo configurable con la variable `TRANSLATE_MODEL`.

## SEO, RSS y analítica (scripts/build_site.py)
Tras actualizar y traducir, `build_site.py` genera:
- una página por ayuda en `docs/ayuda/` (castellano) y `docs/eu/ayuda/` (euskera, solo si hay título traducido), con título, descripción, datos estructurados (JSON-LD) y enlaces `hreflang`;
- `sitemap.xml`, `robots.txt`, `feed.xml` y `feed-eu.xml` (RSS con las 30 ayudas más recientes);
- las etiquetas SEO de `docs/index.html` (entre `<!--SEO-->` y `<!--/SEO-->`; no las edites a mano).

**URL pública:** en GitHub Actions se deduce sola (`https://USUARIO.github.io/REPO`). En local, o con dominio propio, ponla en `site.json` (`"url"`) o en la variable `SITE_URL`; sin URL no se generan sitemap ni feed.

**Analítica sin cookies:** crea una cuenta en goatcounter.com, elige un código (p. ej. `ayudas-euskadi`) y ponlo en `site.json` (`"goatcounter"`). Sin código no se carga nada.

**Después de publicar:** da de alta `https://USUARIO.github.io/REPO/sitemap.xml` en Google Search Console.

Orden en local: `update_data.py` → `translate_eu.py` → `build_site.py`.
