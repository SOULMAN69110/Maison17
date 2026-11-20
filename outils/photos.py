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

Lieu des photos (bouton 📍 du diaporama) : Google ne le donne ni dans l'album ni dans la page
de la photo, mais il le laisse dans le fichier original (balises EXIF GPS), sauf si le
propriétaire a choisi de masquer la position dans les partages. On ne télécharge que le
début de chaque original (64 ko), une seule fois par photo : les positions trouvées sont
gardées dans « geo » (identifiant Google de la photo → [latitude, longitude], 0 = aucune),
et chaque passage complète au plus GEO_MAX photos en GEO_S secondes.
Usage : python3 outils/photos.py photos/albums.txt photos/albums.json
"""
import hashlib, html, json, re, struct, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

RELIRE_H = 6
VERSION = "5"     # à changer pour forcer une relecture complète après une modification de ce programme
GEO_MAX, GEO_S = 1500, 150
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
        return it[0], {"i": it[0], "u": u.split("=")[0], "l": int(it[1][1]), "h": int(it[1][2]),
                       "d": int(it[2]) if isinstance(it[2], (int, float)) else None}
    except Exception:
        return None


def extraire(d):
    """Dans un bloc de Google : la liste des photos, puis le jeton (texte) de la page suivante juste après.
    Aujourd'hui [None, [photos…], "jeton", [album…], …] ; on cherche plutôt que de compter les cases."""
    for i, x in enumerate(d or []):
        if isinstance(x, list) and x and photo_depuis(x[0]):
            suite = d[i + 1] if i + 1 < len(d) else None
            return x, (suite if isinstance(suite, str) and suite else None)
    return [], None


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
        liste, jeton = extraire(d)
        ajouter(liste)
    except Exception as e:
        infos.append("%s : données ds:1 illisibles (%s), lecture simple" % (titre, e))
    if not photos:                              # secours : recherche directe dans la page
        for p in PHOTO.finditer(page):
            if p.group(1) in vues:
                continue
            vues.add(p.group(1))
            d = DATE.search(page, p.end(), p.end() + 2000)
            photos.append({"i": p.group(1), "u": p.group(2).split("=")[0], "l": int(p.group(3)), "h": int(p.group(4)),
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
        liste, jeton = extraire(d)
        if not ajouter(liste):
            break
    photos.sort(key=lambda x: x["d"] or 0)
    dates = [x["d"] for x in photos if x["d"]]
    return {"titre": titre, "lien": lien, "adresse": adresse, "id": album_id, "nb": len(photos),
            "debut": min(dates) if dates else None, "fin": max(dates) if dates else None,
            "photos": photos}


def gps_exif(b):
    """[latitude, longitude] des balises EXIF GPS d'un début de fichier JPEG (ou HEIC), None sinon."""
    i = b.find(b"Exif\x00\x00")
    if i < 0:
        return None
    t = b[i + 6:]
    e = "<" if t[:2] == b"II" else ">"

    def ifd(o):
        n = struct.unpack(e + "H", t[o:o + 2])[0]
        r = {}
        for k in range(n):
            q = o + 2 + 12 * k
            tag, typ, nb = struct.unpack(e + "HHI", t[q:q + 8])
            r[tag] = (typ, nb, t[q + 8:q + 12])
        return r

    def rationnels(v):
        o = struct.unpack(e + "I", v[2])[0]
        x = struct.unpack(e + "6I", t[o:o + 24])
        return x[0] / x[1] + x[2] / x[3] / 60 + x[4] / x[5] / 3600

    z = ifd(struct.unpack(e + "I", t[4:8])[0])
    if 0x8825 not in z:
        return None
    g = ifd(struct.unpack(e + "I", z[0x8825][2])[0])
    if not all(k in g for k in (1, 2, 3, 4)):
        return None
    lat, lon = rationnels(g[2]), rationnels(g[4])
    if g[1][2][:1] == b"S":
        lat = -lat
    if g[3][2][:1] == b"W":
        lon = -lon
    if (lat, lon) == (0, 0) or abs(lat) > 90 or abs(lon) > 180:
        return None
    return [round(lat, 5), round(lon, 5)]


def lire_gps(photo):
    """Position d'une photo : None si la lecture a échoué (à réessayer), 0 si elle n'en a pas."""
    req = urllib.request.Request(photo["u"] + "=d", headers={"User-Agent": NAVIGATEUR, "Range": "bytes=0-65535"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            b = r.read(65536)
    except Exception:
        return None
    try:
        return gps_exif(b) or 0
    except Exception:
        return 0


def completer_geo(albums, geo):
    """Ajoute à chaque photo sa position « g » ; relit l'original de celles qu'on n'a jamais vues. Rend le nombre de photos lues."""
    a_lire, vus = [], set()
    for a in albums:
        for p in a["photos"]:
            if p.get("i") and p["i"] not in geo and p["i"] not in vus:
                vus.add(p["i"]); a_lire.append(p)
    a_lire = a_lire[:GEO_MAX]
    debut, lues = time.time(), 0
    if a_lire:
        with ThreadPoolExecutor(8) as ex:
            for p, g in zip(a_lire, ex.map(lambda p: None if time.time() - debut > GEO_S else lire_gps(p), a_lire)):
                if g is not None:
                    geo[p["i"]] = g; lues += 1
    for a in albums:
        for p in a["photos"]:
            g = geo.get(p.get("i"))
            if g:
                p["g"] = g
            else:
                p.pop("g", None)
    return lues


def manque_geo(albums, geo):
    return any(p.get("i") and p["i"] not in geo for a in albums for p in a["photos"])


def main(liste, sortie):
    liens = lire_liens(liste)
    empreinte = hashlib.sha256((VERSION + "\n" + "\n".join(liens)).encode()).hexdigest()[:16]
    ancien = {}
    try:
        ancien = json.load(open(sortie, encoding="utf-8"))
    except Exception:
        pass
    geo = ancien.get("geo") or {}
    if ancien.get("liste") == empreinte and time.time() - ancien.get("maj", 0) < RELIRE_H * 3600:
        if not manque_geo(ancien.get("albums", []), geo):
            print("Photos : liste à jour, rien à relire")
            return
        n = completer_geo(ancien["albums"], geo)       # liste à jour : on complète seulement les lieux
        ancien["geo"] = geo
        json.dump(ancien, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print("Photos : lieux relevés pour %d photos (%d avec position)" % (n, sum(1 for v in geo.values() if v)))
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
            print("Photos : album lu, %d photos" % a["nb"])
        except Exception as e:
            erreurs.append({"lien": lien, "erreur": str(e)[:200]})
            print("Photos : échec pour un album (%s)" % type(e).__name__)
            if lien in precedents:             # on garde la version d'avant plutôt que rien
                albums.append(precedents[lien])
    albums.sort(key=lambda a: a.get("fin") or 0, reverse=True)
    n = completer_geo(albums, geo)
    print("Photos : lieux relevés pour %d photos (%d avec position)" % (n, sum(1 for v in geo.values() if v)))
    json.dump({"maj": int(time.time()), "liste": empreinte, "albums": albums, "erreurs": erreurs, "infos": infos, "geo": geo},
              open(sortie, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
