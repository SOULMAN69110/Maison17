"""Récupère l'état du chauffage Home-SmartLink (Carrera) et l'écrit dans un JSON pour le site.

Lecture seule : ce script ne change jamais le mode ni la consigne des radiateurs.
Il se connecte avec l'e-mail et le mot de passe de l'appli Home-SmartLink, rangés dans
les secrets GitHub HSL_EMAIL et HSL_MOT_DE_PASSE (jamais écrits dans le fichier publié).

Utilise la bibliothèque non officielle « homesmartlink » (Python 3.13 ou plus récent).
La température mesurée vient d'un « diagnostic » : on demande à la box d'interroger
les thermostats, on attend sa réponse (une minute au plus), puis on lit le résultat.

Usage : python3 outils/chauffage.py site/chauffage.json
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

MODES = {1: "Arrêt", 2: "Hors-gel", 3: "Manuel", 4: "Programme"}


def ecrire(chemin, donnees):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)


def nombre(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, 1)


async def lire(email, mot_de_passe):
    import aiohttp
    from homesmartlink import HomeSmartLinkClient

    async with aiohttp.ClientSession() as session:
        client = HomeSmartLinkClient(session, email, mot_de_passe)
        maisons = await client.login()
        if not maisons:
            raise RuntimeError("aucune maison sur ce compte")
        home_id = maisons[0].home_id
        maison = await client.get_home(home_id)

        # Diagnostic pour avoir des températures récentes (sinon on garde le dernier connu)
        diagnostic = "non demandé"
        try:
            d_id = await client.request_diagnosis(home_id)
            diagnostic = "sans réponse de la box"
            fin = time.time() + 60
            while time.time() < fin:
                await asyncio.sleep(5)
                if (await client.get_diagnosis(d_id)).acknowledged:
                    diagnostic = "ok"
                    break
        except Exception as e:  # le diagnostic est facultatif
            diagnostic = "échec (" + type(e).__name__ + ")"

        etat = await client.get_device_status(home_id)
        box = None
        try:
            box = await client.get_gateway(home_id)
        except Exception:
            pass

        pieces = []
        for r in maison.rooms:
            hs = r.heater_settings
            st = etat.rooms.get(r.number)
            mode = int(hs.current_mode)
            pieces.append({
                "numero": r.number,
                "nom": r.name or ("Pièce " + str(r.number + 1)),
                "mode": MODES.get(mode, "Mode " + str(mode)),
                "mode_code": mode,
                "consigne_manuelle": nombre(hs.manual_value),
                "consigne_confort": nombre(hs.standard_value),
                "consigne_eco": nombre(hs.economy_value),
                "consigne_actuelle": nombre(st.set_point) if st else None,
                "temperature": nombre(st.ambient_temperature) if st else None,
                "fenetre_ouverte_detection": r.open_window_detection_enabled,
                # Programmation : « avancée » = plages 1 à 6, « simplifiée » = matin (7), journée (9), soir (8).
                # jours : 0 = lundi … 6 = dimanche ; mode de plage 1 = confort, 2 = boost, 3 = ventilation
                "programmation": "simplifiée" if r.ecopilot_enabled else "avancée",
                "plages": [{
                    "plage": e.event_id,
                    "jours": [j for j in range(7) if e.recurrence & (1 << j)],
                    "debut": "%02d:%02d" % (e.start_hour, e.start_minute),
                    "fin": "%02d:%02d" % (e.end_hour, e.end_minute),
                    "mode": e.mode,
                } for e in r.events],
            })

        return {
            "disponible": True,
            "maj": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mesure": etat.created_at.isoformat() if etat.created_at else None,
            "diagnostic": diagnostic,
            "vacances_retour": maison.vacation_return_date.isoformat() if maison.vacation_return_date else None,
            "box_derniere_connexion": box.last_connection.isoformat() if box and box.last_connection else None,
            "pieces": pieces,
        }


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else "chauffage.json"
    email_brut, mdp_brut = os.environ.get("HSL_EMAIL", ""), os.environ.get("HSL_MOT_DE_PASSE", "")
    email, mdp = email_brut.strip(), mdp_brut.strip()   # espaces ou retour à la ligne collés par erreur dans les secrets
    if email != email_brut or mdp != mdp_brut:
        print("Chauffage : espaces retirés autour de l'e-mail ou du mot de passe.")
    if not email or not mdp:
        ecrire(chemin, {"disponible": False, "raison": "identifiants Home-SmartLink non renseignés"})
        print("Chauffage : secrets HSL_EMAIL / HSL_MOT_DE_PASSE absents, rien à lire.")
        return
    try:
        donnees = asyncio.run(lire(email, mdp))
        print("Chauffage : " + str(len(donnees["pieces"])) + " pièce(s), diagnostic " + donnees["diagnostic"])
    except Exception as e:
        # Le message d'erreur peut contenir des détails de la réponse : on ne publie que le type
        donnees = {"disponible": False, "raison": "connexion impossible (" + type(e).__name__ + ")"}
        # Dans le journal seulement (GitHub y masque les secrets) : le message aide à comprendre l'échec
        print("Chauffage : échec, " + type(e).__name__ + " : " + str(e)[:300])
        print("Chauffage : e-mail de " + str(len(email)) + " caractères" + ("" if "@" in email else ", sans @ (est-ce bien l'e-mail ?)"))
    ecrire(chemin, donnees)


if __name__ == "__main__":
    main()
