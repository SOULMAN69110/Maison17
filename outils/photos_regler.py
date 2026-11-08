#!/usr/bin/env python3
"""Modifie la page Photos depuis la tâche « Photos : réglages » (lancée par photos.html).
Variables : AJOUTER (lien d'album), RETIRER (lien d'album), REGLAGES (JSON du diaporama).
Tout est vérifié ici : la tâche ne peut écrire que photos/albums.txt et photos/reglages.json."""
import json, os, re, sys

LISTE, REGLAGES = "photos/albums.txt", "photos/reglages.json"
LIEN = re.compile(r"^https://(photos\.app\.goo\.gl|photos\.google\.com/share|goo\.gl)/[\w\-/?=&%.]+$")
PERMIS = {
    "secondes": lambda v: isinstance(v, int) and 2 <= v <= 300,
    "transition": lambda v: v in ("fondu", "noir", "glisse", "zoom", "aucune"),
    "ordre": lambda v: v in ("chrono", "hasard"),
    "legende": lambda v: v in ("oui", "non"),
    "recents": lambda v: isinstance(v, int) and 1 <= v <= 20,
    "veille": lambda v: isinstance(v, str) and re.match(r"^(non|dernier|tous|[\w\-]{8,80})$", v) is not None,
    "veille_min": lambda v: isinstance(v, int) and 1 <= v <= 120,
}

ajouter = os.environ.get("AJOUTER", "").strip()
retirer = os.environ.get("RETIRER", "").strip()
reglages = os.environ.get("REGLAGES", "").strip()

lignes = open(LISTE, encoding="utf-8").read().splitlines()
liens = [l.split("#", 1)[0].strip() for l in lignes]

if ajouter:
    if not LIEN.match(ajouter):
        sys.exit("Lien refusé : %r" % ajouter)
    if ajouter in liens:
        print("Album déjà présent")
    else:
        lignes.append(ajouter); print("Album ajouté :", ajouter)
if retirer:
    avant = len(lignes)
    lignes = [l for l in lignes if l.split("#", 1)[0].strip() != retirer]
    print("Album retiré" if len(lignes) < avant else "Album introuvable dans la liste : %s" % retirer)
if ajouter or retirer:
    open(LISTE, "w", encoding="utf-8").write("\n".join(lignes) + "\n")

if reglages:
    try:
        r = json.loads(reglages)
    except ValueError:
        sys.exit("Réglages illisibles")
    actuels = {}
    try:
        actuels = json.load(open(REGLAGES, encoding="utf-8"))
    except Exception:
        pass
    for k, v in r.items():
        if k in PERMIS and PERMIS[k](v):
            actuels[k] = v
        else:
            print("Réglage ignoré :", k, v)
    json.dump(actuels, open(REGLAGES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Réglages :", actuels)
