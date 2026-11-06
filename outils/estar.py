"""Récupère les données de l'installation solaire eStar Power (monitor.estarpower.com).

Identifiants lus dans les secrets GitHub ESTAR_UTILISATEUR et ESTAR_MOT_DE_PASSE (jamais affichés).
Écrit site/solaire.json (chiffres utiles seulement, aucun jeton) et ajoute une ligne à
historique/solaire-AAAA-MM.csv quand la mesure est nouvelle.

Sans identifiants ou en cas d'erreur, écrit {"disponible": false} et ne fait pas échouer la tâche.

Usage : python3 outils/estar.py site/solaire.json
"""
import base64
import csv
import hashlib
import json
import os
import sys
import time
from datetime import date, timedelta
import http.client
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

STATION = 7054590          # numéro de l'installation (visible dans l'adresse de la page eStar)
API = "https://monitor.estarpower.com/platform/api/gateway"
PARIS = ZoneInfo("Europe/Paris")
MISE_EN_SERVICE = date(2024, 10, 30)   # premier jour de l'installation
JOURS_PAR_PASSAGE = 150                # rattrapage de l'historique par paquets, pour garder des passages courts
FICHIER_JOURS = "historique/solaire-jours.csv"


def appel(chemin, corps, jeton=None):
    """POST JSON. Le jeton part comme dans le navigateur : en-tête « authorization » en minuscules
    (http.client ne change pas la casse, contrairement à urllib) et cookie estar_token."""
    u = urllib.parse.urlsplit(API + chemin)
    entetes = {"content-type": "application/json", "accept": "application/json, text/plain, */*",
               "user-agent": "Mozilla/5.0 (Maison17 tableau de bord)", "language": "fr-fr"}
    if jeton:
        entetes["authorization"] = jeton
        entetes["cookie"] = "estar_token=" + urllib.parse.quote(jeton, safe="")
    cnx = (http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection)(u.netloc, timeout=30)
    try:
        cnx.request("POST", u.path, body=json.dumps(corps).encode(), headers=entetes)
        return json.loads(cnx.getresponse().read().decode("utf-8"))
    finally:
        cnx.close()


def chercher_jeton(obj):
    """Le jeton est rangé dans une clé "token", à un niveau qui peut varier."""
    if isinstance(obj, dict):
        if isinstance(obj.get("token"), str) and obj["token"]:
            return obj["token"]
        for v in obj.values():
            t = chercher_jeton(v)
            if t:
                return t
    return None


def mot_de_passe_chiffre(mdp):
    """Même transformation que la page de connexion eStar : md5 + "." + base64(sha256)."""
    b = mdp.encode("utf-8")
    return hashlib.md5(b).hexdigest() + "." + base64.b64encode(hashlib.sha256(b).digest()).decode()


def nombre(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main(sortie):
    resultat = {"disponible": False}
    utilisateur = os.environ.get("ESTAR_UTILISATEUR", "").strip()
    mdp = os.environ.get("ESTAR_MOT_DE_PASSE", "")
    try:
        if not utilisateur or not mdp:
            raise RuntimeError("identifiants eStar absents (secrets GitHub)")
        connexion = appel("/iam/auth_login", {"user_name": utilisateur, "password": mot_de_passe_chiffre(mdp)})
        jeton = chercher_jeton(connexion)
        print("eStar : connexion", "réussie" if jeton else "sans jeton",
              "| statut", connexion.get("status"), "| clés", sorted((connexion.get("data") or {}).keys()) if isinstance(connexion.get("data"), dict) else type(connexion.get("data")).__name__,
              "| longueur du jeton", len(jeton or ""))
        if not jeton:
            raise RuntimeError("connexion refusée : " + str(connexion.get("message", "sans message")))
        rep = appel("/pvm-data/data_count_station_real_data", {"sid": STATION}, jeton)
        if str(rep.get("status")) != "0":
            raise RuntimeError("données refusées : " + str(rep.get("message", "sans message")))
        d = rep.get("data") or {}
        f = d.get("reflux_station_data") or {}
        resultat = {
            "disponible": True,
            "mesure": d.get("data_time"),                      # heure locale de la dernière mesure
            "puissance_kw": d.get("capacitor"),                # puissance crête de l'installation
            "production_w": nombre(f.get("pv_power") or d.get("real_power")),
            "consommation_w": nombre(f.get("load_power")),
            "reseau_w": nombre(f.get("grid_power")),           # négatif : achat au réseau ; positif : envoi vers le réseau (conso = prod - réseau)
            "jour": bilan_du_jour(d, f),
            "mois_production_wh": nombre(d.get("month_eq")),
            "annee_production_wh": nombre(d.get("year_eq")),
            "total_production_wh": nombre(d.get("total_eq")),
            "taux_autoconsommation": nombre(d.get("self_rate")),
        }
        try:
            completer_avec_courbe(resultat, jeton)
        except Exception as e:
            print("eStar : courbe du jour non lue :", str(e)[:200])
        historiser(resultat)
        try:
            completer_jours(jeton)
        except Exception as e:
            print("eStar : historique par jour non complété :", str(e)[:200])
        try:
            completer_courbes(jeton)
        except Exception as e:
            print("eStar : historique des courbes non complété :", str(e)[:200])
    except Exception as e:  # on ne bloque jamais la publication du tableau de bord
        resultat["erreur"] = str(e)[:200]
        print("eStar :", resultat["erreur"])
    with open(sortie, "w", encoding="utf-8") as fh:
        json.dump(resultat, fh, ensure_ascii=False)


def completer_avec_courbe(r, jeton):
    """Ajoute la courbe du jour (points toutes les 15 min depuis minuit, nuit comprise : le compteur côté Linky
    est relevé même quand l'onduleur dort). Si elle est plus récente que la mesure de l'onduleur, son dernier
    point sert de mesure en direct, et le bilan du jour est demandé pour aujourd'hui."""
    auj = datetime.now(PARIS).date()
    c = courbe_du_jour(jeton, auj.isoformat())
    jour_courbe = auj
    if len(c["heures"]) < 2:                      # juste après minuit : on garde la courbe d'hier
        jour_courbe = auj - timedelta(days=1)
        c = courbe_du_jour(jeton, jour_courbe.isoformat())
    h, se = c["heures"], c["series"]
    prod, conso, res = se.get("grid_power") or [], se.get("consumption_power") or [], se.get("grid_p_power") or []
    def arrondi(v):
        return [round(x) for x in v] if len(v) == len(h) else []
    r["courbe"] = {"date": jour_courbe.isoformat(), "heures": h,
                   "production_w": arrondi(prod), "consommation_w": arrondi(conso), "reseau_w": arrondi(res)}
    try:
        enregistrer_courbe(jour_courbe, c)
    except Exception as e:
        print("eStar : courbe non enregistrée :", str(e)[:200])
    if jour_courbe != auj or not h:
        return
    derniere = auj.isoformat() + " " + h[-1] + ":00"
    if (r.get("mesure") or "") < derniere:
        r["mesure"] = derniere
        r["mesure_source"] = "courbe"
        if len(prod) == len(h): r["production_w"] = float(prod[-1])
        if len(conso) == len(h): r["consommation_w"] = float(conso[-1])
        if len(res) == len(h): r["reseau_w"] = float(res[-1])
        # Bilan d'aujourd'hui : celui de la plateforme, sinon l'intégrale de la courbe (pas de 15 min)
        j = None
        try:
            b = bilan_periode(jeton, 1, auj.isoformat())
            if b.get("consommation_wh") is not None and (not b.get("debut") or b["debut"] == auj.isoformat()):
                j = {k: b.get(k) for k in ("production_wh", "consommation_wh", "autoconsommee_wh", "achetee_wh", "vendue_wh")}
        except Exception as e:
            print("eStar : bilan d'aujourd'hui non lu :", str(e)[:200])
        if j is None and len(conso) == len(h):
            p_wh = sum(prod) * 0.25 if len(prod) == len(h) else 0.0
            achat = sum(-x for x in res if x < 0) * 0.25 if len(res) == len(h) else None
            vente = sum(x for x in res if x > 0) * 0.25 if len(res) == len(h) else None
            j = {"production_wh": p_wh, "consommation_wh": sum(conso) * 0.25, "achetee_wh": achat, "vendue_wh": vente,
                 "autoconsommee_wh": max(0.0, p_wh - vente) if vente is not None else None}
        if j:
            r["jour"] = j


# ===== Historique des courbes (un point toutes les 15 min) : historique/solaire-courbe-AAAA-MM.csv =====
# Colonnes : horodatage (Unix), production_w, consommation_w, reseau_w (négatif : achat).
# historique/solaire-courbe-vides.txt liste les jours sans aucune donnée chez eStar (pour ne pas les redemander).
COURBES_PAR_PASSAGE = 30
FICHIER_VIDES = "historique/solaire-courbe-vides.txt"


def _chemin_courbe(jour):
    return "historique/solaire-courbe-%s.csv" % jour.strftime("%Y-%m")


def _lire_courbe_mois(chemin):
    lignes = []
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            for i, l in enumerate(fh):
                if i and l.strip():
                    lignes.append(l.rstrip("\n").split(","))
    return lignes


def enregistrer_courbe(jour, c):
    """Remplace dans le fichier du mois les points du jour donné par ceux de la courbe c."""
    h, se = c["heures"], c["series"]
    prod, conso, res = se.get("grid_power") or [], se.get("consumption_power") or [], se.get("grid_p_power") or []
    def val(v, k):
        return ("%.0f" % v[k]) if len(v) == len(h) else ""
    debut = int(datetime(jour.year, jour.month, jour.day, tzinfo=PARIS).timestamp())
    lend = jour + timedelta(days=1)
    fin = int(datetime(lend.year, lend.month, lend.day, tzinfo=PARIS).timestamp())
    nouveaux = []
    for k, hh in enumerate(h):
        try:
            t = datetime(jour.year, jour.month, jour.day, int(hh[:2]), int(hh[3:5]), tzinfo=PARIS)
        except ValueError:
            continue
        nouveaux.append([str(int(t.timestamp())), val(prod, k), val(conso, k), val(res, k)])
    chemin = _chemin_courbe(jour)
    garde = [l for l in _lire_courbe_mois(chemin) if not (debut <= int(l[0]) < fin)]
    toutes = sorted(garde + nouveaux, key=lambda l: int(l[0]))
    os.makedirs("historique", exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as fh:
        fh.write("horodatage,production_w,consommation_w,reseau_w\n")
        for l in toutes:
            fh.write(",".join(l) + "\n")
    return len(nouveaux)


def completer_courbes(jeton):
    """Rattrape les courbes des jours passés (les plus récents d'abord), et relit hier tant qu'il est incomplet."""
    auj = datetime.now(PARIS).date()
    vides = set()
    if os.path.exists(FICHIER_VIDES):
        with open(FICHIER_VIDES, encoding="utf-8") as fh:
            vides = {l.strip() for l in fh if l.strip()}
    # jours présents et heure du dernier point de chaque jour
    presents, mois_lus = {}, set()
    j = auj - timedelta(days=1)
    a_lire = []
    while j >= MISE_EN_SERVICE and len(a_lire) < COURBES_PAR_PASSAGE:
        m = j.strftime("%Y-%m")
        if m not in mois_lus:
            mois_lus.add(m)
            for l in _lire_courbe_mois(_chemin_courbe(j)):
                d = datetime.fromtimestamp(int(l[0]), PARIS)
                presents[d.date()] = max(presents.get(d.date(), ""), d.strftime("%H:%M"))
        cle = j.isoformat()
        if cle not in vides:
            if j not in presents or (j == auj - timedelta(days=1) and presents[j] < "23:45"):
                a_lire.append(j)
        j -= timedelta(days=1)
    nouveaux_vides = []
    for j in a_lire:
        try:
            c = courbe_du_jour(jeton, j.isoformat())
        except Exception as e:
            print("eStar : courbe du %s non lue : %s" % (j, str(e)[:120]))
            continue
        if len(c["heures"]) == 0:
            if j < auj - timedelta(days=2):
                nouveaux_vides.append(j.isoformat())
            continue
        enregistrer_courbe(j, c)
        time.sleep(0.15)
    if nouveaux_vides:
        with open(FICHIER_VIDES, "a", encoding="utf-8") as fh:
            fh.write("\n".join(nouveaux_vides) + "\n")
    if a_lire:
        print("eStar : %d courbe(s) de jours passés lue(s)" % len(a_lire))


def bilan_du_jour(d, f):
    """Énergies du jour, à partir des seuls compteurs « today_eq » (les champs *_total de la réponse
    peuvent valoir le cumul depuis l'installation selon le contexte de l'appel)."""
    prod = nombre(d.get("today_eq"))
    achat = nombre((f.get("mb_in_eq") or f.get("grid_in_eq") or {}).get("today_eq"))
    vente = nombre((f.get("mb_out_eq") or f.get("grid_out_eq") or {}).get("today_eq"))
    auto = prod - vente if prod is not None and vente is not None else None
    if auto is not None and auto < 0:
        auto = 0.0
    conso = auto + achat if auto is not None and achat is not None else None
    return {"production_wh": prod, "consommation_wh": conso, "autoconsommee_wh": auto,
            "achetee_wh": achat, "vendue_wh": vente}


def bilan_periode(jeton, mode, quand):
    """Bilan d'une période : mode 1 = jour (AAAA-MM-JJ), 2 = semaine, 3 = mois, 4 = année (AAAA).
    Le corps doit être enveloppé dans « body » pour que le mode et la date soient pris en compte."""
    rep = appel("/pvm-data/data_count_station_real_data",
                {"body": {"sid": STATION, "mode": mode, "date": quand}, "WAITING_PROMISE": True}, jeton)
    if str(rep.get("status")) != "0":
        raise RuntimeError("bilan refusé : " + str(rep.get("message", "")))
    f = (rep.get("data") or {}).get("reflux_station_data") or {}
    prod, achat, vente = nombre(f.get("pv_eq_total")), nombre(f.get("meter_b_in_eq")), nombre(f.get("meter_b_out_eq"))
    auto = nombre(f.get("self_eq"))
    if auto is None and prod is not None and vente is not None:
        auto = max(0.0, prod - vente)
    conso = nombre(f.get("use_eq_total"))
    return {"debut": f.get("start_date"), "fin": f.get("end_date"), "production_wh": prod, "consommation_wh": conso,
            "autoconsommee_wh": auto, "achetee_wh": achat, "vendue_wh": vente}


def completer_jours(jeton):
    """historique/solaire-jours.csv : une ligne par jour terminé depuis la mise en service.
    Rattrape les jours manquants (les plus récents d'abord) et relit les deux derniers jours,
    dont les chiffres peuvent encore s'ajuster après minuit."""
    lignes = {}
    if os.path.exists(FICHIER_JOURS):
        with open(FICHIER_JOURS, encoding="utf-8") as fh:
            for ligne in csv.DictReader(fh):
                lignes[ligne["date"]] = ligne
    hier = datetime.now(PARIS).date() - timedelta(days=1)
    a_lire, j = [], hier
    while j >= MISE_EN_SERVICE:
        cle = j.isoformat()
        if cle not in lignes or (hier - j).days < 2 and lignes[cle].get("relu") != "1":
            a_lire.append(j)
        j -= timedelta(days=1)
    a_lire = a_lire[:JOURS_PAR_PASSAGE]
    for j in a_lire:
        b = bilan_periode(jeton, 1, j.isoformat())
        if b["debut"] and b["debut"] != j.isoformat():
            raise RuntimeError("date inattendue dans la réponse : " + str(b["debut"]))
        lignes[j.isoformat()] = {
            "date": j.isoformat(),
            "production_wh": fmt(b["production_wh"]), "consommation_wh": fmt(b["consommation_wh"]),
            "autoconsommee_wh": fmt(b["autoconsommee_wh"]), "achetee_wh": fmt(b["achetee_wh"]), "vendue_wh": fmt(b["vendue_wh"]),
            # relu = 1 : lu au moins deux jours après, chiffres définitifs
            "relu": "1" if (hier - j).days >= 1 else "0",
        }
        time.sleep(0.15)
    if a_lire:
        os.makedirs("historique", exist_ok=True)
        champs = ["date", "production_wh", "consommation_wh", "autoconsommee_wh", "achetee_wh", "vendue_wh", "relu"]
        with open(FICHIER_JOURS, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=champs, lineterminator="\n")
            w.writeheader()
            for cle in sorted(lignes):
                w.writerow({k: lignes[cle].get(k, "") for k in champs})
        reste = sum(1 for k in range((hier - MISE_EN_SERVICE).days + 1)
                    if (MISE_EN_SERVICE + timedelta(days=k)).isoformat() not in lignes)
        print("eStar : %d jour(s) lus, %d encore à rattraper" % (len(a_lire), reste))


def fmt(v):
    return "" if v is None else ("%.0f" % v)


def historiser(r):
    """Une ligne par nouvelle mesure dans historique/solaire-AAAA-MM.csv."""
    if not r.get("mesure"):
        return
    quand = datetime.strptime(r["mesure"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=PARIS)
    ts = int(quand.timestamp())
    chemin = "historique/solaire-%s.csv" % quand.strftime("%Y-%m")
    deja = set()
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            deja = {ligne.split(",")[0] for ligne in fh}
    if str(ts) in deja:
        return
    nouveau = not os.path.exists(chemin)
    os.makedirs("historique", exist_ok=True)
    with open(chemin, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nouveau:
            w.writerow(["horodatage", "production_w", "consommation_w", "reseau_w", "production_jour_wh", "consommation_jour_wh"])
        j = r["jour"]
        w.writerow([ts, r["production_w"], r["consommation_w"], r["reseau_w"], j["production_wh"], j["consommation_wh"]])


# ===== Courbe du jour à la minute (serveur des courbes Hoymiles, sur lequel repose eStar) =====
# Le site eStar l'obtient par POST JSON {sid, date} et reçoit un message protobuf « LineChart » :
#   LineChart  : 1 xAxis (chaînes répétées, heures), 2 series (LineSeries répétées), 3 type
#   LineSeries : 1 type (ex. "power", "consumption_power", "grid_power"), 2 data (flottants répétés), 3 did, 4 port
HOTES_COURBES = ["https://neapi.hoymiles.com", "https://euapi.hoymiles.com"]


def _varint(b, i):
    n = dec = 0
    while True:
        c = b[i]; i += 1
        n |= (c & 0x7F) << dec; dec += 7
        if c < 0x80:
            return n, i


def _champs(b):
    """Décodage protobuf minimal : liste de (numéro, type, valeur brute)."""
    i, out = 0, []
    while i < len(b):
        cle, i = _varint(b, i)
        num, typ = cle >> 3, cle & 7
        if typ == 0:
            v, i = _varint(b, i)
        elif typ == 1:
            v = b[i:i + 8]; i += 8
        elif typ == 2:
            n, i = _varint(b, i); v = b[i:i + n]; i += n
        elif typ == 5:
            v = b[i:i + 4]; i += 4
        else:
            raise ValueError("type protobuf inattendu %d" % typ)
        out.append((num, typ, v))
    return out


def decoder_courbe(b):
    import struct
    heures, series = [], {}
    for num, typ, v in _champs(b):
        if num == 1 and typ == 2:
            heures.append(v.decode("utf-8", "replace"))
        elif num == 2 and typ == 2:
            nom, vals = "", []
            for n2, t2, v2 in _champs(v):
                if n2 == 1 and t2 == 2:
                    nom = v2.decode("utf-8", "replace")
                elif n2 == 2 and t2 == 2:        # flottants « packed »
                    vals.extend(struct.unpack("<%df" % (len(v2) // 4), v2))
                elif n2 == 2 and t2 == 5:
                    vals.append(struct.unpack("<f", v2)[0])
            series[nom] = vals
    return {"heures": heures, "series": series}


def courbe_du_jour(jeton, jour):
    """Courbe du jour (AAAA-MM-JJ) : {"heures": [...], "series": {type: [valeurs]}}."""
    derniere = None
    for hote in HOTES_COURBES:
        u = urllib.parse.urlsplit(hote + "/pvm-data/api/0/station/data/count_power_by_day")
        cnx = http.client.HTTPSConnection(u.netloc, timeout=30)
        try:
            cnx.request("POST", u.path, body=json.dumps({"sid": STATION, "date": jour}).encode(),
                        headers={"content-type": "application/json", "accept": "application/json, text/plain, */*",
                                 "user-agent": "Mozilla/5.0 (Maison17 tableau de bord)", "authorization": jeton,
                                 "cookie": "estar_token=" + urllib.parse.quote(jeton, safe=""), "language": "fr-fr"})
            r = cnx.getresponse(); b = r.read()
        finally:
            cnx.close()
        if b[:2] == b"\x1f\x8b":          # réponse compressée (gzip)
            import gzip
            b = gzip.decompress(b)
        if r.status == 200 and b and not b.lstrip().startswith(b"{"):
            return decoder_courbe(b)          # peut être vide (jour sans données)
        derniere = "%s : HTTP %s %s" % (u.netloc, r.status, b[:120])
    raise RuntimeError("courbe du jour indisponible (" + str(derniere) + ")")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site/solaire.json")
