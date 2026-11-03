"""Ajoute les dernières mesures (Mobile Alerts + pression Open-Meteo) aux fichiers CSV mensuels.

Usage : python3 outils/historiser.py site/data.json meteo.json
Fichiers produits (heure de Paris pour le découpage par mois) :
  historique/mesures-AAAA-MM.csv  : horodatage,capteur,temp,hum,temp_ext,hum_ext
  historique/pression-AAAA-MM.csv : horodatage,pression_hpa
"""
import csv, json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
DOSSIER = "historique"


def fichier(prefixe, ts, entete):
    mois = datetime.fromtimestamp(ts, PARIS).strftime("%Y-%m")
    chemin = os.path.join(DOSSIER, f"{prefixe}-{mois}.csv")
    if not os.path.exists(chemin):
        with open(chemin, "w", newline="") as f:
            csv.writer(f).writerow(entete)
    return chemin


def derniers(chemin, cle):
    """Dernier horodatage enregistré par clé (capteur), pour ne pas dupliquer."""
    vus = {}
    if os.path.exists(chemin):
        with open(chemin, newline="") as f:
            for ligne in csv.DictReader(f):
                vus[ligne[cle]] = max(vus.get(ligne[cle], 0), int(ligne["horodatage"]))
    return vus


def valeur(m, k):
    v = m.get(k)
    return "" if v is None else v


def main(mesures_json, meteo_json):
    os.makedirs(DOSSIER, exist_ok=True)
    ajouts = 0
    try:
        appareils = json.load(open(mesures_json)).get("devices", [])
    except Exception:
        appareils = []
    for a in appareils:
        m = a.get("measurement") or {}
        ts = m.get("ts")
        if not ts or m.get("t1") is None:
            continue
        chemin = fichier("mesures", ts, ["horodatage", "capteur", "temp", "hum", "temp_ext", "hum_ext"])
        if derniers(chemin, "capteur").get(a["deviceid"], 0) >= ts:
            continue
        with open(chemin, "a", newline="") as f:
            csv.writer(f).writerow([ts, a["deviceid"], m["t1"], valeur(m, "h"), valeur(m, "t2"), valeur(m, "h2")])
        ajouts += 1

    try:
        meteo = json.load(open(meteo_json))
        p = meteo["current"]["pressure_msl"]
        ts = int(meteo["current"]["time"])  # demandé en timeformat=unixtime
        chemin = fichier("pression", ts, ["horodatage", "pression_hpa"])
        with open(chemin, newline="") as f:
            lignes = list(csv.reader(f))
        if len(lignes) < 2 or int(lignes[-1][0]) < ts:
            with open(chemin, "a", newline="") as f:
                csv.writer(f).writerow([ts, p])
            ajouts += 1
    except Exception as e:
        print("pression ignorée :", e)

    # Liste des fichiers disponibles, lue par la page de courbes
    liste = sorted(n for n in os.listdir(DOSSIER) if n.endswith(".csv"))
    with open(os.path.join(DOSSIER, "index.json"), "w") as f:
        json.dump(liste, f)
    print(f"{ajouts} ligne(s) ajoutée(s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
