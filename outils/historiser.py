"""Ajoute les dernières mesures (Mobile Alerts + pression Open-Meteo) aux fichiers CSV mensuels.

Usage : python3 outils/historiser.py site/data.json meteo.json [site/chauffage.json]
Fichiers produits (heure de Paris pour le découpage par mois) :
  historique/mesures-AAAA-MM.csv   : horodatage,capteur,temp,hum,temp_ext,hum_ext
  historique/pression-AAAA-MM.csv  : horodatage,pression_hpa
  historique/chauffage-AAAA-MM.csv : horodatage,piece,temperature,consigne,mode
    (radiateurs Home-SmartLink ; horodatage = heure du relevé par la box)
  historique/etat-radiateur-AAAA-MM.csv : horodatage,piece,brut,d,s,j,w,m,y
    (ligne d'état brute du thermostat découpée ; D, S inconnus, J/W/M/Y peut-être la consommation)
"""
import csv, json, os, re, sys
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


def champs_brut(brut):
    """R7D0M4S0C43A42J0W0M0Y0 -> [D, S, J, W, M, Y], lus dans l'ordre (le 2e M est le compteur)."""
    m = re.fullmatch(r"R\d+D(\d+)M\d+S(\d+)C\d+A\d+J(\d+)W(\d+)M(\d+)Y(\d+)", brut or "")
    return list(m.groups()) if m else [""] * 6


def main(mesures_json, meteo_json, chauffage_json=None):
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

    if chauffage_json:
        try:
            ch = json.load(open(chauffage_json))
            if ch.get("disponible") and ch.get("mesure"):
                ts = int(datetime.fromisoformat(ch["mesure"]).timestamp())
                for pc in ch.get("pieces", []):
                    if pc.get("temperature") is None:
                        continue
                    chemin = fichier("chauffage", ts, ["horodatage", "piece", "temperature", "consigne", "mode"])
                    if derniers(chemin, "piece").get(str(pc["numero"]), 0) >= ts:
                        continue
                    with open(chemin, "a", newline="") as f:
                        csv.writer(f).writerow([ts, pc["numero"], pc["temperature"], valeur(pc, "consigne_actuelle"), valeur(pc, "mode_code")])
                    ajouts += 1
            for pc in ch.get("pieces", []):
                brut = pc.get("etat_brut")
                if not brut:
                    continue
                chemin = fichier("etat-radiateur", ts, ["horodatage", "piece", "brut", "d", "s", "j", "w", "m", "y"])
                if derniers(chemin, "piece").get(str(pc["numero"]), 0) >= ts:
                    continue
                with open(chemin, "a", newline="") as f:
                    csv.writer(f).writerow([ts, pc["numero"], brut] + champs_brut(brut))
                ajouts += 1
        except Exception as e:
            print("chauffage ignoré :", e)

    # Liste des fichiers disponibles, lue par la page de courbes
    liste = sorted(n for n in os.listdir(DOSSIER) if n.endswith(".csv"))
    with open(os.path.join(DOSSIER, "index.json"), "w") as f:
        json.dump(liste, f)
    print(f"{ajouts} ligne(s) ajoutée(s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
