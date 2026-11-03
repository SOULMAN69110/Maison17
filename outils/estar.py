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
import http.client
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

STATION = 7054590          # numéro de l'installation (visible dans l'adresse de la page eStar)
API = "https://monitor.estarpower.com/platform/api/gateway"
PARIS = ZoneInfo("Europe/Paris")


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
        historiser(resultat)
    except Exception as e:  # on ne bloque jamais la publication du tableau de bord
        resultat["erreur"] = str(e)[:200]
        print("eStar :", resultat["erreur"])
    with open(sortie, "w", encoding="utf-8") as fh:
        json.dump(resultat, fh, ensure_ascii=False)


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


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site/solaire.json")
