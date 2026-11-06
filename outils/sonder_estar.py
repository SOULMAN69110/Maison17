"""Provisoire : essaie l'adresse eStar de la courbe du jour et affiche la forme de la réponse (sans jeton)."""
import json, sys
sys.path.insert(0, "outils")
import estar, os
from datetime import datetime
jeton = estar.chercher_jeton(estar.appel("/iam/auth_login", {"user_name": os.environ["ESTAR_UTILISATEUR"], "password": estar.mot_de_passe_chiffre(os.environ["ESTAR_MOT_DE_PASSE"])}))
auj = datetime.now(estar.PARIS).strftime("%Y-%m-%d")
for chemin in ["/pvm-data/api/0/station/data/count_power_by_day", "/pvm-data/api/0/station/data/p_day_s_a", "/pvm-data/api/0/station/data/count_eq_by_day"]:
    for corps in [{"body": {"sid": estar.STATION, "date": auj}, "WAITING_PROMISE": True}, {"sid": estar.STATION, "date": auj}]:
        try:
            r = estar.appel(chemin, corps, jeton)
            t = json.dumps(r, ensure_ascii=False)
            print("=====", chemin, "| enveloppé" if "body" in corps else "| direct", "| longueur", len(t))
            print(t[:2500])
        except Exception as e:
            print("=====", chemin, "erreur", e)
