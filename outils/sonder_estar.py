"""Provisoire : teste la courbe du jour eStar (n'affiche jamais le jeton)."""
import os, sys
sys.path.insert(0, "outils")
import estar
from datetime import datetime, timedelta
jeton = estar.chercher_jeton(estar.appel("/iam/auth_login", {"user_name": os.environ["ESTAR_UTILISATEUR"], "password": estar.mot_de_passe_chiffre(os.environ["ESTAR_MOT_DE_PASSE"])}))
for j in [datetime.now(estar.PARIS).date(), datetime.now(estar.PARIS).date() - timedelta(days=1)]:
    try:
        c = estar.courbe_du_jour(jeton, j.isoformat())
        h = c["heures"]
        print("=====", j, "| points", len(h), "| de", h[:3], "à", h[-3:])
        for nom, v in c["series"].items():
            nz = [x for x in v if x]
            print("   série %-22s n=%d  min=%s max=%s  début=%s  fin=%s" % (nom, len(v), min(v) if v else None, max(v) if v else None, [round(x) for x in v[:4]], [round(x) for x in v[-4:]]))
    except Exception as e:
        print("=====", j, "erreur", e)
