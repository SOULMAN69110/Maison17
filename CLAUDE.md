# Maison17 — tableau de bord de la maison

Tableau de bord de la maison (69110, Sainte-Foy-lès-Lyon) : capteurs Mobile Alerts, météo (Open-Meteo, Météo-France pour la pluie dans l'heure), panneaux solaires eStar Power (Hoymiles), radiateur Carrera (Home-SmartLink), albums Google Photos. Site statique publié sur **GitHub Pages** (https://soulman69110.github.io/Maison17/), affiché sur la **télé Samsung** (navigateur intégré ou recopie iPhone → Apple TV) et sur l'**iPhone** (webapp sur l'écran d'accueil).

**Le [README.md](README.md) est la fiche complète** (pages, capteurs, fonctionnement, fichiers, entretien, historique du projet) : le lire en début de session et le tenir à jour à chaque évolution (section « Historique du projet », datée).

Utilisateur : Hervé, francophone. **Toujours répondre en français, y compris dans les descriptions de commandes et les annonces entre deux actions** (redemandé plusieurs fois).

## Fonctionnement en bref

- Pas de serveur : pages HTML/JS à la racine (`index.html`, `historique.html`, `energie.html`, `bilans.html`, `chauffage.html`, `lieux.html`, `photos.html`, `meteo.html`), scripts communs `nav.js` (rangée de boutons), `verrou.js` (phrase d'accès et déchiffrement des données), `veille.js` (écran de veille photos), `maj.js` (rechargement à chaque nouvelle version).
- **GitHub Actions** (`.github/workflows/`) : `pages.yml` (« Mesures et publication » : interroge les sources, ajoute aux CSV de `historique/`, publie `data.json`, `solaire.json`, `chauffage.json`, `photos/albums.json`), `horloge.yml` (relance toutes les 10 min), `chauffage-regler.yml` et `photos-regler.yml` (lancées depuis les pages avec un jeton GitHub à granularité fine gardé sur l'appareil). Scripts Python dans `outils/`.
- Secrets dans GitHub (Settings → Secrets → Actions) : `ESTAR_*`, `HSL_*`, `MAISON17_PHRASE` (phrase d'accès, clé du chiffrement), `MOBILE_ALERTS` (`nom=ID` des capteurs)… Jamais de secret, jeton ni identifiant personnel dans le dépôt : **il est public**, comme le site.
- **Données chiffrées** (depuis le 9/11/2026, voir README « Protection des données ») : l'historique est sur la branche `donnees`, chiffré (`outils/coffre.js`), jamais en clair sur `main` ni sur le site ; les pages déchiffrent via `verrou.js` (leurs `fetch()` sont interceptés). Seule la météo (`?vue=meteo`, `lieux.html?retour=meteo`) est libre. Ne jamais remettre de données, d'ID de capteur ni de lien d'album en clair dans le dépôt, dans le site ou dans les journaux des tâches (publics).

## Façon de travailler

- **Le robot enregistre l'historique toutes les 10 minutes** sur la branche `donnees` (un seul commit remplacé à chaque fois), et non plus sur `main` : faire quand même `git pull --rebase` avant de commencer et avant de pousser (la page Photos peut modifier `photos/reglages.json`).
- Publier = pousser sur `main` (la tâche republie le site ; pour une page nouvelle, l'ajouter à la copie de `pages.yml`, à `PAGES` de `nav.js` et à `RACCOURCIS` d'`index.html`). Vérifier ensuite que la tâche est passée (onglet Actions) et que la page en ligne a changé.
- Git : si `git` n'est pas reconnu, `& "$env:ProgramFiles\Git\cmd\git.exe"` ; messages de commit en français, écrits dans un fichier et passés par `-F`.
- **Télé Samsung QLED Q9FN (2018)** : son navigateur ne connaît ni la grille CSS, ni `inset`, ni `min()` → garder les mises en page de secours en flexbox (`@supports not (display:grid)`) et tester toute modification de mise en page en pensant à elle ; télécommande : flèches, OK, Retour.
- **iPhone (16 Pro Max) à l'horizontale** et webapp installée : vérifier l'affichage paysage (zones sûres, bas de page) ; le stockage de la webapp est séparé de Safari (jeton à recoller une fois).
- Vérifier son travail sur toutes les pages touchées avant de dire que c'est publié (Hervé l'a demandé).
- Fin de session : Hervé dit « fin de session » ; mettre alors le README à jour.

## À reprendre (choix d'Hervé)

- Alertes automatiques (pile faible, box du chauffage hors ligne, capteur muet) envoyées par la tâche : ntfy, e-mail, WhatsApp (CallMeBot) ou SMS (Free Mobile) ; veilleur extérieur (healthchecks.io) pour les mesures figées — « nous verrons plus tard ».
- Voyant « en chauffe » du radiateur : comprendre les champs `D`, `S` et les compteurs `J`/`W`/`M`/`Y` de l'état brut (`historique/etat-radiateur-*.csv`), Linky pas encore relié à Home-SmartLink.
- Apps iOS / Android sur les stores : mises de côté le 5/11/2026 (voir le document du projet claude.ai, recopié dans `discussions/projet-claude-ai.md`).
- Écartées pour l'instant : appli Apple TV native (pas de Mac), SmartThings.

## Discussions d'origine

Les conversations claude.ai du projet (3 au 9 novembre 2026) sont dans `discussions/` (une par fichier, index `discussions/INDEX.md`). Ce dossier est **exclu de Git** (`.git/info/exclude`) : données personnelles, ne jamais le pousser sur le dépôt public.
