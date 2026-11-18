#!/usr/bin/env python3
"""
Escribe releases.json: la última release de cada mod de mods.json y del propio manager.

El manager lo descarga de raw.githubusercontent.com, que no gasta el cupo de la API (60 consultas por hora sin
token); así no tiene que preguntar a GitHub por cada mod. Lo genera la Action "Releases" con su token.

Uso: build_releases.py <mods.json> <salida>
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

# Repos que no son mods pero cuya release consulta el manager: él mismo, para avisar de versiones nuevas.
EXTRA_REPOS = ["d1ll3x3/FIH_ModManager"]


def github(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "FIH-ModCatalog"})
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def latest_release(repo):
    # Igual que el manager: la última release estable o, si solo hay prereleases, la más reciente.
    release = github(f"https://api.github.com/repos/{repo}/releases/latest")
    if release is None:
        releases = github(f"https://api.github.com/repos/{repo}/releases?per_page=1")
        release = releases[0] if releases else None
    if release is None:
        return None
    # Mismos nombres de campo que la API, para que el manager lo lea igual que una respuesta de GitHub.
    return {
        "tag_name": release["tag_name"],
        "name": release.get("name"),
        "body": release.get("body"),
        "published_at": release.get("published_at"),
        "html_url": release["html_url"],
        "assets": [
            {
                "name": a["name"],
                "browser_download_url": a["browser_download_url"],
                "size": a["size"],
                "download_count": a.get("download_count", 0),
            }
            for a in release.get("assets", [])
        ],
    }


def main():
    source, output = sys.argv[1], sys.argv[2]
    with open(source, encoding="utf-8") as f:
        repos = [m["repo"] for m in json.load(f)["mods"]] + EXTRA_REPOS

    releases = {}
    for repo in dict.fromkeys(repos):
        try:
            releases[repo] = latest_release(repo)
        except (urllib.error.URLError, TimeoutError) as e:
            # Un repo que falla no deja a los demás sin actualizar; el manager lo consultará él mismo.
            print(f"{repo}: {e}", file=sys.stderr)

    # Sin hora de generación: así el archivo solo cambia (y solo se hace commit) cuando cambia alguna release.
    with open(output, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"releases": releases}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{output}: {sum(r is not None for r in releases.values())} of {len(releases)} repos with a release")


if __name__ == "__main__":
    main()
