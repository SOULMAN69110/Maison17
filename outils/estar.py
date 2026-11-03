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
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

STATION = 7054590          # numéro de l'installation (visible dans l'adresse de la page eStar)
API = "https://monitor.estarpower.com/platform/api/gateway"
PARIS = ZoneInfo("Europe/Paris")


def appel(chemin, corps, jeton=None):
    entetes = {"Content-Type": "application/json", "User-Agent": "Maison17-tableau-de-bord"}
    if jeton:
        entetes["authorization"] = jeton
    req = urllib.request.Request(API + chemin, data=json.dumps(corps).encode(), headers=entetes, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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
            "jour": {
                "production_wh": nombre(f.get("pv_eq_total") or d.get("today_eq")),
                "consommation_wh": nombre(f.get("use_eq_total")),
                "autoconsommee_wh": nombre(f.get("self_eq")),
                "achetee_wh": nombre(f.get("meter_b_in_eq")),
                "vendue_wh": nombre(f.get("meter_b_out_eq")),
            },
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
