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
import hashlib, html, json, re, sys, time, urllib.parse, urllib.request

RELIRE_H = 6
VERSION = "3"     # à changer pour forcer une relecture complète après une modification de ce programme
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


def photo_depuis(it):
    """Une photo des données de Google : [id, [url, largeur, hauteur, …], date_ms, …]"""
    try:
        u = it[1][0]
        if not (isinstance(u, str) and u.startswith("https://lh3.googleusercontent.com/")):
            return None
        return it[0], {"u": u.split("=")[0], "l": int(it[1][1]), "h": int(it[1][2]),
                       "d": int(it[2]) if isinstance(it[2], (int, float)) else None}
    except Exception:
        return None


def donnees_ds1(page):
    """Le bloc de données « ds:1 » de la page de l'album : [[photos…], jeton de la page suivante, …]"""
    m = re.search(r"AF_initDataCallback\(\{key: 'ds:1',.*?data:(\[.*?\]), sideChannel", page, re.S)
    return json.loads(m.group(1)) if m else None


def page_suivante(album_id, cle, jeton, adresse):
    """Photos suivantes de l'album (Google en envoie 300 à la fois) : appel « snAcKc » de la page Google Photos."""
    freq = json.dumps([[["snAcKc", json.dumps([album_id, jeton, None, cle]), None, "generic"]]])
    url = ("https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=snAcKc&source-path=%s&hl=fr&rt=c"
           % urllib.parse.quote(urllib.parse.urlparse(adresse).path))
    req = urllib.request.Request(url, data=urllib.parse.urlencode({"f.req": freq}).encode(),
                                 headers={"User-Agent": NAVIGATEUR, "Referer": adresse,
                                          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=40) as r:
        texte = r.read().decode("utf-8", "replace")
    for ligne in texte.splitlines():
        if '"wrb.fr"' in ligne and "snAcKc" in ligne:
            for bloc in json.loads(ligne):
                if bloc[0] == "wrb.fr" and bloc[1] == "snAcKc" and bloc[2]:
                    return json.loads(bloc[2])
    raise ValueError("réponse de Google sans photos")


def lire_album(lien, infos):
    page, adresse = telecharger(lien)
    m = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    titre = html.unescape(m.group(1)).strip() if m else ""
    titre = re.sub(r"\s*[-–·]\s*Google Photos$", "", titre) or "Album"
    photos, vues = [], set()

    def ajouter(liste):
        n = 0
        for it in liste or []:
            r = photo_depuis(it)
            if r and r[0] not in vues:
                vues.add(r[0]); photos.append(r[1]); n += 1
        return n

    jeton = None
    try:
        d = donnees_ds1(page)
        ajouter(d[0]); jeton = d[1] if len(d) > 1 and isinstance(d[1], str) else None
        infos.append("%s : ds:1 = %s" % (titre, [(type(x).__name__, (len(x) if isinstance(x, (list, str)) else x)) for x in d[:8]]))
    except Exception as e:
        infos.append("%s : données ds:1 illisibles (%s), lecture simple" % (titre, e))
    if not photos:                              # secours : recherche directe dans la page
        for p in PHOTO.finditer(page):
            if p.group(1) in vues:
                continue
            vues.add(p.group(1))
            d = DATE.search(page, p.end(), p.end() + 2000)
            photos.append({"u": p.group(2).split("=")[0], "l": int(p.group(3)), "h": int(p.group(4)),
                           "d": int(d.group(1)) if d else None})
    # Pages suivantes
    chemin = urllib.parse.urlparse(adresse)
    album_id = chemin.path.rstrip("/").split("/")[-1]
    cle = (urllib.parse.parse_qs(chemin.query).get("key") or [None])[0]
    pages = 0
    while jeton and pages < 40:
        try:
            d = page_suivante(album_id, cle, jeton, adresse)
        except Exception as e:
            infos.append("%s : arrêt après %d photos (%s)" % (titre, len(photos), str(e)[:150]))
            break
        pages += 1
        if not ajouter(d[0]):
            break
        jeton = d[1] if len(d) > 1 and isinstance(d[1], str) else None
    photos.sort(key=lambda x: x["d"] or 0)
    dates = [x["d"] for x in photos if x["d"]]
    return {"titre": titre, "lien": lien, "adresse": adresse, "id": album_id, "nb": len(photos),
            "debut": min(dates) if dates else None, "fin": max(dates) if dates else None,
            "photos": photos}


def main(liste, sortie):
    liens = lire_liens(liste)
    empreinte = hashlib.sha256((VERSION + "\n" + "\n".join(liens)).encode()).hexdigest()[:16]
    ancien = {}
    try:
        ancien = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        pass
    if ancien.get("liste") == empreinte and time.time() - ancien.get("maj", 0) < RELIRE_H * 3600:
        print("Photos : liste à jour, rien à relire")
        return
    precedents = {a["lien"]: a for a in ancien.get("albums", [])}
    albums, erreurs, infos, deja = [], [], [], set()
    for lien in liens:
        try:
            a = lire_album(lien, infos)
            if not a["photos"]:
                raise ValueError("aucune photo trouvée (album non partagé par lien ?)")
            if a["id"] in deja:                # deux liens vers le même album
                infos.append("%s : présent deux fois dans la liste" % a["titre"])
                continue
            deja.add(a["id"])
            albums.append(a)
            print("Photos : %s — %d photos" % (a["titre"], a["nb"]))
        except Exception as e:
            erreurs.append({"lien": lien, "erreur": str(e)[:200]})
            print("Photos : échec pour %s : %s" % (lien, e))
            if lien in precedents:             # on garde la version d'avant plutôt que rien
                albums.append(precedents[lien])
    albums.sort(key=lambda a: a.get("fin") or 0, reverse=True)
    json.dump({"maj": int(time.time()), "liste": empreinte, "albums": albums, "erreurs": erreurs, "infos": infos},
              open(sortie, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
