#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — Generatore del repository plugin QGIS.

Cosa fa, in automatico:
  1. Trova tutti i file .zip nella cartella (ogni zip = un plugin QGIS).
  2. Apre ogni zip e legge il metadata.txt che sta al suo interno.
  3. Se dello stesso plugin ci sono piu' versioni, tiene solo la piu' recente.
  4. Estrae l'icona di ogni plugin nella cartella icons/.
  5. Rigenera plugins.xml (il file che QGIS legge) e index.html (pagina web).

L'URL di download viene costruito da solo:
  - su GitHub Actions usa la variabile GITHUB_REPOSITORY per capire owner/repo
    e comporre l'indirizzo di GitHub Pages;
  - in locale puoi forzarlo con la variabile d'ambiente REPO_BASE_URL,
    es:  REPO_BASE_URL="https://mario.github.io/qgis-repo-ftth/" python build.py

Non richiede librerie esterne: gira con qualsiasi Python 3 (anche quello di QGIS).
"""

import os
import re
import sys
import glob
import zipfile
import datetime
import configparser
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(HERE, "icons")


# --------------------------------------------------------------------------- #
# URL di base (GitHub Pages)
# --------------------------------------------------------------------------- #
def detect_base_url():
    base = os.environ.get("REPO_BASE_URL", "").strip()
    if not base:
        gh = os.environ.get("GITHUB_REPOSITORY", "").strip()  # "owner/repo"
        if "/" in gh:
            owner, repo = gh.split("/", 1)
            if repo.lower() == f"{owner.lower()}.github.io":
                base = f"https://{owner}.github.io/"
            else:
                base = f"https://{owner}.github.io/{repo}/"
    if not base:
        base = "https://TUOUSERNAME.github.io/qgis-repo-ftth/"
        print("ATTENZIONE: URL di base non rilevato, uso un segnaposto.\n"
              "            Su GitHub verra' impostato in automatico.\n"
              "            In locale puoi impostare REPO_BASE_URL.\n"
              f"            Segnaposto attuale: {base}")
    return base.rstrip("/") + "/"


# --------------------------------------------------------------------------- #
# Confronto versioni (0.69 < 0.70 < 1.0), senza dipendenze esterne
# --------------------------------------------------------------------------- #
def version_key(v):
    parts = []
    for chunk in re.findall(r"\d+|[A-Za-z]+", str(v)):
        if chunk.isdigit():
            parts.append((1, int(chunk), ""))
        else:
            parts.append((0, 0, chunk.lower()))
    return tuple(parts) or ((1, 0, ""),)


# --------------------------------------------------------------------------- #
# Lettura del metadata.txt dall'interno dello zip
# --------------------------------------------------------------------------- #
def read_plugin(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

        meta_member = next(
            (n for n in names if n.split("/")[-1] == "metadata.txt"), None
        )
        if not meta_member:
            print(f"  ! {os.path.basename(zip_path)}: nessun metadata.txt, saltato")
            return None

        # cartella di primo livello del plugin (es. "FTTH_PERMIT_MANAGER")
        plugin_dir = meta_member.split("/")[0] if "/" in meta_member else ""

        raw = zf.read(meta_member).decode("utf-8", errors="replace")
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.read_string(raw)
        if not cp.has_section("general"):
            print(f"  ! {os.path.basename(zip_path)}: sezione [general] mancante, saltato")
            return None
        g = cp["general"]

        def get(k, default=""):
            return (g.get(k, default) or "").strip()

        icon_rel = get("icon")
        icon_url_name = ""
        if icon_rel and plugin_dir:
            icon_member = f"{plugin_dir}/{icon_rel}"
            if icon_member in names:
                os.makedirs(ICONS_DIR, exist_ok=True)
                ext = os.path.splitext(icon_rel)[1] or ".png"
                icon_url_name = f"{plugin_dir}{ext}"
                with open(os.path.join(ICONS_DIR, icon_url_name), "wb") as fh:
                    fh.write(zf.read(icon_member))

        # normalizza spazi nei campi multi-linea (about/description)
        def flat(s):
            return re.sub(r"\s+", " ", s).strip()

        return {
            "zip_file": os.path.basename(zip_path),
            "name": get("name") or plugin_dir or os.path.basename(zip_path),
            "version": get("version") or "0.0.0",
            "description": flat(get("description")),
            "about": flat(get("about")),
            "qgis_min": get("qgisMinimumVersion") or "3.0",
            "qgis_max": get("qgisMaximumVersion") or "3.99",
            "author": get("author") or get("author_name"),
            "email": get("email"),
            "homepage": get("homepage"),
            "tracker": get("tracker"),
            "repository": get("repository"),
            "tags": get("tags"),
            "experimental": get("experimental") or "False",
            "deprecated": get("deprecated") or "False",
            "icon_name": icon_url_name,
        }


# --------------------------------------------------------------------------- #
# Generazione plugins.xml
# --------------------------------------------------------------------------- #
def build_xml(plugins, base_url, today):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<plugins>"]
    for p in plugins:
        dl = base_url + quote(p["zip_file"]) + "?v=" + quote(p["version"])
        icon_url = base_url + "icons/" + quote(p["icon_name"]) if p["icon_name"] else ""
        lines += [
            f'  <pyqgis_plugin name={quoteattr(p["name"])} version={quoteattr(p["version"])}>',
            f'    <description>{escape(p["description"])}</description>',
            f'    <about>{escape(p["about"])}</about>',
            f'    <version>{escape(p["version"])}</version>',
            f'    <qgis_minimum_version>{escape(p["qgis_min"])}</qgis_minimum_version>',
            f'    <qgis_maximum_version>{escape(p["qgis_max"])}</qgis_maximum_version>',
            f'    <homepage>{escape(p["homepage"])}</homepage>',
            f'    <file_name>{escape(p["zip_file"])}</file_name>',
            f'    <icon>{escape(icon_url)}</icon>',
            f'    <author_name>{escape(p["author"])}</author_name>',
            f'    <download_url>{escape(dl)}</download_url>',
            f'    <uploaded_by>{escape(p["author"])}</uploaded_by>',
            f'    <create_date>{today}</create_date>',
            f'    <update_date>{today}</update_date>',
            f'    <experimental>{escape(p["experimental"])}</experimental>',
            f'    <deprecated>{escape(p["deprecated"])}</deprecated>',
            f'    <tracker>{escape(p["tracker"])}</tracker>',
            f'    <repository>{escape(p["repository"])}</repository>',
            f'    <tags>{escape(p["tags"])}</tags>',
            "  </pyqgis_plugin>",
        ]
    lines.append("</plugins>")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Generazione index.html (pagina informativa)
# --------------------------------------------------------------------------- #
def build_html(plugins, base_url, today):
    xml_url = base_url + "plugins.xml"
    rows = ""
    for p in plugins:
        icon = (f'<img src="icons/{quote(p["icon_name"])}" alt="" '
                f'width="40" height="40">') if p["icon_name"] else ""
        rows += f"""
      <tr>
        <td>{icon}</td>
        <td><strong>{escape(p['name'])}</strong><br><span class="muted">{escape(p['description'])}</span></td>
        <td><code>{escape(p['version'])}</code></td>
        <td>QGIS &ge; {escape(p['qgis_min'])}</td>
        <td><a href="{quote(p['zip_file'])}">.zip</a></td>
      </tr>"""
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repository plugin QGIS</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         max-width: 820px; margin: 3rem auto; padding: 0 1.2rem; line-height: 1.55; }}
  h1 {{ font-size: 1.5rem; margin-bottom: .2rem; }}
  .url {{ display:flex; gap:.5rem; align-items:center; background:#0000000d;
         border:1px solid #00000022; border-radius:10px; padding:.7rem .9rem; margin:1rem 0; }}
  .url code {{ font-size:.95rem; word-break:break-all; }}
  button {{ cursor:pointer; border:0; border-radius:8px; padding:.5rem .8rem; }}
  table {{ border-collapse:collapse; width:100%; margin-top:1rem; }}
  td, th {{ text-align:left; padding:.55rem .5rem; border-bottom:1px solid #00000018; vertical-align:top; }}
  .muted {{ opacity:.7; font-size:.9rem; }}
  ol {{ padding-left:1.2rem; }}
  code {{ background:#00000010; padding:.05rem .3rem; border-radius:5px; }}
</style>
</head>
<body>
  <h1>Repository plugin QGIS</h1>
  <p class="muted">Aggiornato il {today}</p>

  <p>Per installare i plugin: in QGIS apri <em>Plugin &rarr; Gestisci e installa plugin &rarr; Impostazioni &rarr; Aggiungi&hellip;</em>
     e incolla questo URL come indirizzo del repository:</p>

  <div class="url">
    <code id="u">{xml_url}</code>
    <button onclick="navigator.clipboard.writeText(document.getElementById('u').textContent)">Copia</button>
  </div>

  <table>
    <thead><tr><th></th><th>Plugin</th><th>Versione</th><th>Compatibilit&agrave;</th><th>Download</th></tr></thead>
    <tbody>{rows}
    </tbody>
  </table>

  <h2 style="font-size:1.1rem;margin-top:2rem">Come aggiornare (per chi mantiene il repo)</h2>
  <ol>
    <li>Aumenta il numero di <code>version</code> nel <code>metadata.txt</code> del plugin.</li>
    <li>Rigenera lo .zip.</li>
    <li>Carica il nuovo .zip in questo repository (anche via drag&amp;drop su GitHub).</li>
    <li>Il resto si aggiorna da solo: QGIS proporr&agrave; l'aggiornamento ai colleghi.</li>
  </ol>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
def main():
    base_url = detect_base_url()
    today = datetime.date.today().isoformat()

    zips = sorted(glob.glob(os.path.join(HERE, "*.zip")))
    if not zips:
        print("Nessun file .zip trovato nella cartella. Niente da fare.")
        # scrivo comunque un plugins.xml vuoto valido
        with open(os.path.join(HERE, "plugins.xml"), "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<plugins>\n</plugins>\n')
        return 0

    print(f"URL di base: {base_url}")
    print(f"Trovati {len(zips)} file .zip:")

    parsed = []
    for z in zips:
        p = read_plugin(z)
        if p:
            print(f"  - {p['name']}  v{p['version']}  ({p['zip_file']})")
            parsed.append(p)

    # tieni solo la versione piu' alta per ogni plugin (stesso name)
    latest = {}
    for p in parsed:
        cur = latest.get(p["name"])
        if cur is None or version_key(p["version"]) > version_key(cur["version"]):
            latest[p["name"]] = p
    plugins = sorted(latest.values(), key=lambda x: x["name"].lower())

    xml = build_xml(plugins, base_url, today)
    with open(os.path.join(HERE, "plugins.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)

    html = build_html(plugins, base_url, today)
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"\nOK: generati plugins.xml e index.html con {len(plugins)} plugin.")
    print(f"URL da usare in QGIS: {base_url}plugins.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
