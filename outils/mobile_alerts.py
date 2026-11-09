#!/usr/bin/env python3
"""Dernières mesures des capteurs Mobile Alerts, avec les ID remplacés par des noms.

Les vrais ID des capteurs ne figurent plus dans le dépôt public : ils sont dans le secret GitHub
MOBILE_ALERTS, sous la forme « salon=077B…,bureau=1224… ». Le fichier produit (et l'historique)
ne contient que les noms (salon, bureau…), que les pages connaissent.
Usage : python3 outils/mobile_alerts.py site/data.json
Rien d'identifiant n'est écrit dans le journal de la tâche (public)."""
import json, os, sys, urllib.parse, urllib.request

API = "https://www.data199.com/api/pv1/device/lastmeasurement"


def main(sortie):
    noms = {}
    for paire in os.environ.get("MOBILE_ALERTS", "").split(","):
        if "=" in paire:
            nom, ident = (x.strip() for x in paire.split("=", 1))
            if nom and ident:
                noms[ident.upper()] = nom
    resultat = {"devices": []}
    if not noms:
        print("Mobile Alerts : secret MOBILE_ALERTS absent, aucune mesure.")
    else:
        try:
            corps = urllib.parse.urlencode({"deviceids": ",".join(noms)}).encode()
            req = urllib.request.Request(API, data=corps, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            for a in d.get("devices") or []:
                nom = noms.get(str(a.get("deviceid", "")).upper())
                if nom:
                    a["deviceid"] = nom
                    resultat["devices"].append(a)
            print("Mobile Alerts : %d capteur(s) lu(s)" % len(resultat["devices"]))
        except Exception as e:
            print("Mobile Alerts : échec (%s)" % type(e).__name__)
    json.dump(resultat, open(sortie, "w", encoding="utf-8"), separators=(",", ":"))


if __name__ == "__main__":
    main(sys.argv[1])
