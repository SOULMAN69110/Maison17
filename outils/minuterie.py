"""Ajoute à chauffage.json la minuterie du chauffage en cours, pour l'afficher partout (tableau de bord, page Chauffage).

Usage : python3 outils/minuterie.py site/chauffage.json minuteries.json
minuteries.json = réponse de l'API GitHub « runs » de la tâche chauffage-minuterie.yml (nom « Minuterie N min · pièce P »).
Résultat : "minuterie": {"piece": 7, "minutes": 15, "debut": "…", "fin": "…"} (fin vide tant que la tâche attend
son démarrage), ou null s'il n'y en a pas. Ne fait rien si chauffage.json n'existe pas.
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone


def main(chemin_chauffage, chemin_runs):
    try:
        etat = json.load(open(chemin_chauffage, encoding="utf-8"))
    except (OSError, ValueError):
        print("Minuterie : pas de chauffage.json, rien à faire.")
        return
    try:
        runs = json.load(open(chemin_runs, encoding="utf-8")).get("workflow_runs", [])
    except (OSError, ValueError):
        runs = []
    minuterie = None
    for r in runs:
        if r.get("status") == "completed":
            continue
        m = re.search(r"Minuterie (\d+) min(?: · pièce (\d+))?", r.get("display_title") or r.get("name") or "")
        if not m:
            continue
        minutes, piece = int(m.group(1)), int(m.group(2) or 7)
        debut = r.get("run_started_at") if r.get("status") == "in_progress" else None
        fin = None
        if debut:
            fin_dt = datetime.fromisoformat(debut.replace("Z", "+00:00")) + timedelta(minutes=minutes)
            if fin_dt < datetime.now(timezone.utc):
                continue   # compte à rebours fini : la tâche est en train de remettre le programme
            fin = fin_dt.isoformat(timespec="seconds")
        minuterie = {"piece": piece, "minutes": minutes, "debut": debut, "fin": fin}
        break
    etat["minuterie"] = minuterie
    with open(chemin_chauffage, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1)
    print("Minuterie : " + ("fin vers " + minuterie["fin"] if minuterie and minuterie["fin"] else "en attente" if minuterie else "aucune"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
