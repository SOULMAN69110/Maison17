"""Change les réglages d'un radiateur Home-SmartLink (Carrera) : mode, consigne manuelle, confort, éco.

Lancé par la tâche « Régler le chauffage » (.github/workflows/chauffage-regler.yml), elle-même
déclenchée depuis la page chauffage.html. Les identifiants viennent des secrets HSL_EMAIL et
HSL_MOT_DE_PASSE. Un champ vide veut dire « ne pas changer ».

Variables : PIECE (numéro de la pièce, 7 = SdB filles), MODE (Arrêt, Hors-gel, Manuel, Programme
ou vide), MANUELLE, CONFORT, ECO (en °C, pas de 0,5), PLAGES (JSON, programmation avancée :
[{"plage": 1, "debut": "05:30", "fin": "08:00", "jours": [0, 1, 2, 3, 4]}, …], jours 0 = lundi ;
heures par pas de 10 min ; aucun jour = plage inactive).
"""

import asyncio
import json
import os
import sys
from datetime import time

MODES = {"Arrêt": 1, "Hors-gel": 2, "Manuel": 3, "Programme": 4}


def degres(nom):
    v = os.environ.get(nom, "").strip().replace(",", ".")
    if not v:
        return None
    v = float(v)
    if (v * 2) % 1:
        raise ValueError(nom + " : " + str(v) + " n'est pas un multiple de 0,5 °C")
    return v


def lire_plages():
    v = os.environ.get("PLAGES", "").strip()
    if not v:
        return None
    plages = []
    for p in json.loads(v):
        n = int(p["plage"])
        if not 1 <= n <= 6:
            raise ValueError("plage " + str(n) + " : seules les plages 1 à 6 se modifient")
        h1, m1 = (int(x) for x in p["debut"].split(":"))
        h2, m2 = (int(x) for x in p["fin"].split(":"))
        jours = sorted({int(j) for j in p.get("jours", [])})
        plages.append((n, time(h1, m1), time(h2, m2), jours))
    return plages


async def regler(email, mdp, piece, mode, manuelle, confort, eco, plages):
    import aiohttp
    from homesmartlink import HeaterMode, HomeSmartLinkClient
    from homesmartlink.program import with_advanced_slot, with_program_temperatures

    async with aiohttp.ClientSession() as session:
        client = HomeSmartLinkClient(session, email, mdp)
        home_id = (await client.login())[0].home_id
        avant = (await client.get_home(home_id)).room(piece).heater_settings
        print("Avant : mode " + str(int(avant.current_mode)) + ", manuelle " + str(avant.manual_value)
              + ", confort " + str(avant.standard_value) + ", éco " + str(avant.economy_value))

        if confort is not None or eco is not None:
            await client.update_room(
                home_id, piece, lambda h: with_program_temperatures(h, piece, economy=eco, standard=confort))
            print("Confort / éco envoyés.")

        if plages:
            def editer(h):
                for n, debut, fin, jours in plages:
                    h = with_advanced_slot(h, piece, n, debut, fin, jours)
                return h
            await client.update_program(home_id, editer)
            for n, debut, fin, jours in plages:
                print("Plage " + str(n) + " : " + debut.strftime("%H:%M") + "-" + fin.strftime("%H:%M") + ", jours " + str(jours))

        if mode is not None or manuelle is not None:
            m = HeaterMode(mode) if mode is not None else HeaterMode(int(avant.current_mode))
            await client.set_room_state(home_id, piece, m, manual_value=manuelle)
            print("Mode / consigne manuelle envoyés.")

        apres = (await client.get_home(home_id)).room(piece).heater_settings
        print("Après : mode " + str(int(apres.current_mode)) + ", manuelle " + str(apres.manual_value)
              + ", confort " + str(apres.standard_value) + ", éco " + str(apres.economy_value))


def main():
    email = os.environ.get("HSL_EMAIL", "").strip()
    mdp = os.environ.get("HSL_MOT_DE_PASSE", "").strip()
    if not email or not mdp:
        sys.exit("Réglage : secrets HSL_EMAIL / HSL_MOT_DE_PASSE absents.")
    piece = int(os.environ.get("PIECE", "7"))
    nom_mode = os.environ.get("MODE", "").strip()
    if nom_mode and nom_mode not in MODES:
        sys.exit("Réglage : mode inconnu « " + nom_mode + " ».")
    mode = MODES.get(nom_mode)
    manuelle, confort, eco = degres("MANUELLE"), degres("CONFORT"), degres("ECO")
    plages = lire_plages()
    if mode is None and manuelle is None and confort is None and eco is None and not plages:
        sys.exit("Réglage : rien à changer.")
    asyncio.run(regler(email, mdp, piece, mode, manuelle, confort, eco, plages))


if __name__ == "__main__":
    main()
