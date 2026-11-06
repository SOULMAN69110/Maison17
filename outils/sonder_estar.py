"""Provisoire : affiche le début brut de la réponse de la courbe du jour (jamais le jeton)."""
import os, sys, json, http.client, urllib.parse
sys.path.insert(0, "outils")
import estar
from datetime import datetime
jeton = estar.chercher_jeton(estar.appel("/iam/auth_login", {"user_name": os.environ["ESTAR_UTILISATEUR"], "password": estar.mot_de_passe_chiffre(os.environ["ESTAR_MOT_DE_PASSE"])}))
j = datetime.now(estar.PARIS).date().isoformat()
for hote in estar.HOTES_COURBES:
    u = urllib.parse.urlsplit(hote + "/pvm-data/api/0/station/data/count_power_by_day")
    cnx = http.client.HTTPSConnection(u.netloc, timeout=30)
    cnx.request("POST", u.path, body=json.dumps({"sid": estar.STATION, "date": j}).encode(),
                headers={"content-type": "application/json", "authorization": jeton, "user-agent": "Mozilla/5.0"})
    r = cnx.getresponse(); b = r.read()
    print("=====", u.netloc, r.status, r.getheader("content-type"), r.getheader("content-encoding"), "longueur", len(b))
    print("hex :", b[:160].hex())
    print("texte :", b[:300])
