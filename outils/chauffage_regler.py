"""Change les réglages d'un radiateur Home-SmartLink (Carrera) : mode, consigne manuelle, confort, éco.

Lancé par la tâche « Régler le chauffage » (.github/workflows/chauffage-regler.yml), elle-même
déclenchée depuis la page chauffage.html. Les identifiants viennent des secrets HSL_EMAIL et
HSL_MOT_DE_PASSE. Un champ vide veut dire « ne pas changer ».

Variables : PIECE (numéro de la pièce, 7 = SdB filles), MODE (Arrêt, Hors-gel, Manuel, Programme
ou vide), MANUELLE, CONFORT, ECO (en °C, pas de 0,5).
"""

import asyncio
import os
import sys

MODES = {"Arrêt": 1, "Hors-gel": 2, "Manuel": 3, "Programme": 4}


def degres(nom):
    v = os.environ.get(nom, "").strip().replace(",", ".")
    if not v:
        return None
    v = float(v)
    if (v * 2) % 1:
        raise ValueError(nom + " : " + str(v) + " n'est pas un multiple de 0,5 °C")
    return v


async def regler(email, mdp, piece, mode, manuelle, confort, eco):
    import aiohttp
    from homesmartlink import HeaterMode, HomeSmartLinkClient
    from homesmartlink.program import with_program_temperatures

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
    if mode is None and manuelle is None and confort is None and eco is None:
        sys.exit("Réglage : rien à changer.")
    asyncio.run(regler(email, mdp, piece, mode, manuelle, confort, eco))


if __name__ == "__main__":
    main()
