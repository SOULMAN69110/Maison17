#!/usr/bin/env python3
"""Albums Google Photos de la page Photos.

Google ne laisse plus un site lire la liste des albums d'un compte (avril 2025).
On passe donc par les albums PARTAGÉS PAR LIEN : chaque lien est écrit dans
photos/albums.txt (une ligne par album, « # » pour un commentaire). Pour chaque
lien, ce programme lit la page publique de l'album, en tire le titre, les photos
(adresse, largeur, hauteur, date) et écrit photos/albums.json, trié de l'album
le plus récent (date de sa photo la plus récente) au plus ancien.

Les adresses des photos finissent par changer chez Google : la liste est relue
toutes les 6 h, ou tout de suite si albums.txt a changé.
Usage : python3 outils/photos.py photos/albums.txt photos/albums.json
"""
import hashlib, html, json, re, sys, time, urllib.request

RELIRE_H = 6
NAVIGATEUR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Une photo dans les données de la page : ["AF1Q…",["https://lh3…/pw/…",largeur,hauteur,…],date_ms,…
PHOTO = re.compile(r'\["(AF1Q[\w-]+)",\["(https://lh3\.googleusercontent\.com/pw/[^"]+)",(\d+),(\d+)')
DATE = re.compile(r'\],(1\d{12}),')


def lire_liens(chemin):
    liens = []
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.split("#", 1)[0].strip()
        if ligne.startswith("http"):
            liens.append(ligne.split()[0])
    return liens


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": NAVIGATEUR, "Accept-Language": "fr-FR,fr;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def lire_album(lien):
    page, adresse = telecharger(lien)
    m = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    titre = html.unescape(m.group(1)).strip() if m else ""
    titre = re.sub(r"\s*[-–·]\s*Google Photos$", "", titre) or "Album"
    photos, vues = [], set()
    for p in PHOTO.finditer(page):
        if p.group(1) in vues:
            continue
        vues.add(p.group(1))
        url = p.group(2).split("=")[0]        # sans la taille demandée : la page ajoute =w…-h…
        d = DATE.search(page, p.end(), p.end() + 2000)
        photos.append({"u": url, "l": int(p.group(3)), "h": int(p.group(4)),
                       "d": int(d.group(1)) if d else None})
    dates = [x["d"] for x in photos if x["d"]]
    return {"titre": titre, "lien": lien, "adresse": adresse, "nb": len(photos),
            "debut": min(dates) if dates else None, "fin": max(dates) if dates else None,
            "photos": photos}


def main(liste, sortie):
    liens = lire_liens(liste)
    empreinte = hashlib.sha256("\n".join(liens).encode()).hexdigest()[:16]
    ancien = {}
    try:
        ancien = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        pass
    if ancien.get("liste") == empreinte and time.time() - ancien.get("maj", 0) < RELIRE_H * 3600:
        print("Photos : liste à jour, rien à relire")
        return
    precedents = {a["lien"]: a for a in ancien.get("albums", [])}
    albums, erreurs = [], []
    for lien in liens:
        try:
            a = lire_album(lien)
            if not a["photos"]:
                raise ValueError("aucune photo trouvée (album non partagé par lien ?)")
            albums.append(a)
            print("Photos : %s — %d photos" % (a["titre"], a["nb"]))
        except Exception as e:
            erreurs.append({"lien": lien, "erreur": str(e)[:200]})
            print("Photos : échec pour %s : %s" % (lien, e))
            if lien in precedents:             # on garde la version d'avant plutôt que rien
                albums.append(precedents[lien])
    albums.sort(key=lambda a: a.get("fin") or 0, reverse=True)
    json.dump({"maj": int(time.time()), "liste": empreinte, "albums": albums, "erreurs": erreurs},
              open(sortie, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
