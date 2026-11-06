"""Provisoire : cherche comment eStar sert la courbe du jour (affiche la forme des réponses, jamais le jeton)."""
import json, os, re, sys, urllib.request
sys.path.insert(0, "outils")
import estar
from datetime import datetime

# 1. Contexte d'appel dans les scripts du site
base = "https://monitor.estarpower.com"
html = urllib.request.urlopen(urllib.request.Request(base + "/", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode("utf-8", "replace")
noms = set(re.findall(r'(?:src|href)="([^"]+\.js)"', html))
js = ""
for n in list(noms):
    u = n if n.startswith("http") else base + (n if n.startswith("/") else "/" + n)
    try: js += urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "replace")
    except Exception: pass
for c in set(re.findall(r'"(/platform/js/chunk-[0-9a-f]+\.[0-9a-f]+\.js)"', js)) | set("/platform/js/chunk-%s.%s.js" % m for m in re.findall(r'"(chunk-[0-9a-f]+)":"([0-9a-f]+)"', js)):
    c = c if c.startswith("/platform") else c
    try: js += urllib.request.urlopen(urllib.request.Request(base + c, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "replace")
    except Exception: pass
print("scripts :", len(js))
# fichiers de configuration éventuels
for n in ["/platform/config.js", "/config.js", "/platform/static/config.js", "/platform/js/config.js"]:
    try:
        t = urllib.request.urlopen(urllib.request.Request(base + n, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "replace")
        print("##### fichier", n, len(t)); print(t[:3000])
    except Exception as e:
        print("##### fichier", n, "absent", str(e)[:60])
print("##### scripts cités par la page :", sorted(re.findall(r'(?:src|href)="([^"]+)"', html))[:40])
for motif, avant, apres, maxi in [(r"openHost", 200, 300, 8), (r'"station_day"', 400, 900, 6), (r"ajaxGetPvmProtoData\(", 200, 700, 8),
                                  (r"application/x-protobuf|protobuf", 200, 300, 4), (r"LineChart:\{", 50, 1500, 2), (r'"LineChart"', 100, 1200, 4),
                                  (r"message LineChart", 50, 1500, 2)]:
    vus = 0
    for m in re.finditer(motif, js):
        if vus >= maxi: break
        print("----- %s : %s" % (motif, js[max(0, m.start() - avant): m.end() + apres].replace("\n", " ")))
        vus += 1
sys.exit(0)
# 2. Essais authentifiés
jeton = estar.chercher_jeton(estar.appel("/iam/auth_login", {"user_name": os.environ["ESTAR_UTILISATEUR"], "password": estar.mot_de_passe_chiffre(os.environ["ESTAR_MOT_DE_PASSE"])}))
auj = datetime.now(estar.PARIS).strftime("%Y-%m-%d")
for chemin, corps in [
    ("/pvm-data/data_select_eq_by_date", {"sid": estar.STATION, "date": auj}),
    ("/pvm-data/data_select_eq_by_date", {"sid": estar.STATION, "date": auj, "mode": 1}),
    ("/pvm-data/data_find_details", {"sid": estar.STATION, "date": auj}),
]:
    for env in (True, False):
        c = {"body": corps, "WAITING_PROMISE": True} if env else corps
        try:
            t = json.dumps(estar.appel(chemin, c, jeton), ensure_ascii=False)
            print("=====", chemin, json.dumps(corps), "enveloppé" if env else "direct", "| longueur", len(t)); print(t[:1500])
        except Exception as e:
            print("=====", chemin, "erreur", e)
