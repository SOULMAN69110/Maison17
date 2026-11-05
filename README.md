# Météo-maison17

Tableau de bord de la maison (69110, Sainte-Foy-lès-Lyon), affiché sur la télé Samsung via l'Apple TV. Il réunit les capteurs Mobile Alerts et la météo, et garde l'historique des mesures.

Mis en place le 3 novembre 2026.

## Adresses

| Page | Adresse |
|---|---|
| Tableau de bord (télé) | https://soulman69110.github.io/Maison17/ |
| Courbes et historique | https://soulman69110.github.io/Maison17/historique.html |
| Énergie (panneaux solaires) | https://soulman69110.github.io/Maison17/energie.html |
| Bilans énergie (semaine, mois, année, N/N-1) | https://soulman69110.github.io/Maison17/bilans.html |
| Lieux météo (recherche, ma position, favoris) | https://soulman69110.github.io/Maison17/lieux.html |
| Météo seule, sans code (à partager) | https://soulman69110.github.io/Maison17/meteo.html — avec `?lieu=meze` (ou une autre ville) pour régler le lieu à la première ouverture |
| Appli Météo (à installer sur le téléphone) | ouvrir le lien Météo seule (avec `?lieu=…`), puis iPhone : Safari → Partager → *Sur l'écran d'accueil* ; Android : Chrome → menu ⋮ → *Installer l'application* (ou *Ajouter à l'écran d'accueil*). L'icône ouvre la météo en plein écran, sur le lieu du lien. |
| Mesures brutes (CSV) | dossier [`historique/`](historique/) de ce dépôt |

**Affichage sur la télé** : ouvrir le tableau de bord dans Safari sur l'iPhone, tourner le téléphone à l'horizontale, puis centre de contrôle → Recopie de l'écran → Apple TV. La page s'ouvre aussi directement dans le navigateur de la télé Samsung.

**Directement sur la télé Samsung** (application Internet) : ouvrir `soulman69110.github.io/Maison17`, saisir le code, puis Paramètres (roue dentée) → *Définir comme page d'accueil* → *Page actuelle* : lancer Internet ouvre alors le tableau de bord. On peut aussi l'ajouter aux favoris (étoile). Pour un affichage permanent, vérifier l'arrêt automatique de la télé (Paramètres → Général → Solution Éco → Arrêt automatique). Les intitulés peuvent varier selon la version du logiciel de la télé.

## Capteurs Mobile Alerts

| Pièce | Identifiant | Mesures |
|---|---|---|
| Salon (station) | 077BD6BA8BF6 | température et humidité intérieures et extérieures |
| Chambre C. | 121D9CDE1215 | température, humidité |
| Chambre parents | 121B8C435713 | température, humidité |
| Chambre Y. | 122897FF614E | température, humidité |
| Bureau | 1224E7AD1BFA | température, humidité |
| SdB filles | 202D151D9A21 | température |
| SdB parents | 02129E969BF2 | température |

La pression et le pictogramme de prévision de la station du salon ne sont pas transmis par Mobile Alerts : ils viennent d'Open-Meteo (gratuit, sans clé), pour la position de Sainte-Foy-lès-Lyon.

## Panneaux solaires (eStar Power)

Installation de 4,25 kWc suivie sur monitor.estarpower.com (installation n° 7054590). La tâche se connecte avec les secrets GitHub `ESTAR_UTILISATEUR` et `ESTAR_MOT_DE_PASSE` (Settings → Secrets and variables → Actions ; à mettre à jour si le mot de passe eStar change), puis publie `solaire.json` (chiffres seulement, aucun jeton) et ajoute une ligne à `historique/solaire-AAAA-MM.csv` (`horodatage`, `production_w`, `consommation_w`, `reseau_w` — négatif = achat au réseau —, `production_jour_wh`, `consommation_jour_wh`). Le bilan du jour est calculé à partir des seuls compteurs « du jour » d'eStar. L'historique jour par jour depuis la mise en service (30 octobre 2024) est dans `historique/solaire-jours.csv` (`date`, `production_wh`, `consommation_wh`, `autoconsommee_wh`, `achetee_wh`, `vendue_wh`, `relu`) : demandé à eStar avec `mode` 1 (jour), le corps enveloppé dans `body`, rattrapé par paquets de 150 jours puis complété chaque jour. Les jours de panne du suivi eStar (aucune production et moins de 0,5 kWh consommé, par exemple du 18 au 27 septembre 2026) restent tels quels dans le CSV ; la page Bilans les estime par la moyenne des 7 jours valides avant et après, les hachure et les signale. Si la connexion échoue, la page Énergie l'indique et le reste du tableau de bord continue de fonctionner.

## Fonctionnement

1. Toutes les 10 minutes, la tâche GitHub Actions `Mesures et publication` interroge Mobile Alerts et Open-Meteo. GitHub ne lançant les tâches planifiées que toutes les quelques heures, c'est la tâche `Horloge` (`.github/workflows/horloge.yml`) qui la relance : elle reste active près de 6 h, relance la publication toutes les 10 min, puis la suivante, qu'elle a elle-même programmée dès son démarrage, prend le relais (le déclenchement horaire de GitHub ne suffisait pas).
2. Elle ajoute les nouvelles mesures aux fichiers mensuels `historique/mesures-AAAA-MM.csv` et `historique/pression-AAAA-MM.csv`, et les enregistre dans le dépôt.
3. Elle republie le site sur GitHub Pages avec une copie des dernières mesures (`data.json`).

Mobile Alerts refuse les appels directs depuis un navigateur : c'est pour ça que la page lit la copie publiée par la tâche, et non l'API elle-même. La météo (prévisions et pression affichées) est en revanche lue en direct par la page.

### Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | tableau de bord ; noms et ordre des pièces en tête du script |
| `verrou.js` | écran du code d'accès, commun aux deux pages |
| `energie.html` | page Énergie : production solaire, consommation, réseau, bilan du jour et courbe de la journée |
| `bilans.html` | bilans solaires par semaine, mois, année et comparaison mois par mois avec l'année précédente |
| `outils/estar.py` | récupère les données eStar Power (connexion avec les secrets GitHub) |
| `historique.html` | page de courbes (jour, semaine, mois, année avec flèches ◀ ▶, ou dates libres) |
| `lieux.html` | choix du lieu de la météo : recherche de ville, ma position, historique, favoris (gardés sur chaque appareil) |
| `chauffage.html` | page Chauffage : état du radiateur et réglages (mode, consignes manuelle, confort, éco) ; raccourci visible seulement sur les appareils où le jeton de réglage a été saisi, et toujours dans l'appli installée sur l'écran d'accueil (sur iPhone, son stockage est séparé de Safari : le jeton s'y colle une fois) |
| `outils/chauffage.py`, `outils/chauffage_regler.py` | lecture de l'état du chauffage (à chaque publication) et envoi des réglages |
| `.github/workflows/chauffage-regler.yml` | tâche « Régler le chauffage », lancée par la page Chauffage ou à la main (champ vide = inchangé) |
| `app/` | appli Météo installable : manifeste (`meteo.webmanifest`) et icônes, chargés par `index.html` en vue météo seule |
| `outils/historiser.py` | ajoute les mesures aux CSV sans doublons |
| `.github/workflows/pages.yml` | la tâche automatique ; liste des identifiants à mettre à jour si on ajoute un capteur |
| `.github/workflows/horloge.yml` | relance la tâche automatique toutes les 10 min |

### Format des CSV

- `mesures-AAAA-MM.csv` : `horodatage` (secondes Unix), `capteur`, `temp`, `hum`, `temp_ext`, `hum_ext` (les deux dernières pour la station du salon)
- `pression-AAAA-MM.csv` : `horodatage`, `pression_hpa`

## Entretien

- **Code d'accès** : les deux pages demandent un code, retenu un an sur chaque appareil (iPhone, navigateur de la télé). Le code n'est pas écrit dans le dépôt, seulement son empreinte dans `verrou.js`, avec la marche à suivre pour le changer. C'est un écran d'accès dissuasif, pas une vraie protection : le dépôt et les mesures restent publics. Les chambres des enfants sont nommées par leur initiale (Chambre C., Chambre Y.).

- **Si les chiffres se figent** : vérifier dans l'onglet Actions qu'une tâche `Horloge` est en cours ; sinon la lancer (*Run workflow*). GitHub met aussi en pause les tâches planifiées d'un dépôt public après 60 jours sans activité. Les enregistrements d'historique comptent normalement comme activité ; sinon, relancer la tâche depuis l'onglet Actions (*Run workflow*).
- **Ajouter une page** : la créer à la racine, l'ajouter à la commande `cp` de `pages.yml` et à la liste `RACCOURCIS` d'`index.html`.
- **Ajouter un capteur** : l'ajouter dans `CAPTEURS` dans `index.html` et `historique.html`, et dans `IDS` dans `pages.yml`.
- **Piles faibles** au 3 novembre 2026 : Chambre parents, Chambre Y., SdB parents.

## Historique du projet

- **3 nov. 2026** : création du tableau de bord (heure, extérieur, 7 pièces avec confort, humidité et alertes de pile), hébergement sur GitHub Pages, ajout de la pression et des prévisions sur 4 jours, démarrage de l'historique des mesures et de la page de courbes.
- **3 nov. 2026 (suite)** : émojis sur les blocs Dehors, Prévisions et sur chaque pièce ; courbe de la pression du jour avec échelle des deux côtés ; prévisions sur 7 jours ; mise en page adaptée à l'iPhone à l'horizontale ; écran de code d'accès sur les deux pages ; chambres des enfants nommées Chambre C. et Chambre Y. ; volet roulant sur la partie intérieure, fermé par défaut et refermé automatiquement au bout de 3 min (`VOLET_MIN` dans `index.html`). Ajout de la pluie dans l'heure : 4 bâtonnets par quart d'heure (Open-Meteo, précipitations sur 15 min), plus hauts et plus sombres selon l'intensité (faible < 0,25 mm, modérée < 0,75, forte < 2, très forte au-delà) ; météo rafraîchie toutes les 15 min. Le volet fermé affiche les prévisions sur 15 jours avec les températures du matin (8 h), du midi (13 h), du soir (19 h) et de la nuit suivante (2 h), avec des bâtonnets de hauteur et couleur selon la température (échelle commune aux 15 jours) ; jours 11 à 15 plus pâles (simple tendance) ; la page se recharge seule quand une nouvelle version est publiée. Colonne de gauche en cadres (Dehors, pluie dans l'heure, pression, prévisions). Ajout de la page Énergie (panneaux solaires eStar Power), compatible avec le navigateur de la télé. Page Bilans (semaine, mois, année, N/N-1, infobulles, jours de panne estimés) ; résumé « production à date » vs N-1 sur la page Énergie ; courbes en 24 h par défaut avec l'échelle répétée à droite. Détail : page Bilans (semaine, mois, année, N/N-1) et raccourcis vers les autres pages à droite de l'heure sur le tableau de bord (liste `RACCOURCIS` en tête du script d'`index.html`).
- **3 nov. 2026 (télé Samsung)** : le navigateur intégré de la télé (QLED Q9FN de 2018) ne connaît ni la grille CSS, ni `inset`, ni `min()`. L'écran du code d'accès restait noir, puis la page s'empilait sur une seule colonne. Ajout d'une mise en page de secours en flexbox dans `index.html` (bloc `@supports not (display:grid)`), ignorée par les navigateurs récents. À garder en tête pour toute modification de mise en page.
- **5 nov. 2026** : les températures ne se mettaient à jour que toutes les 4 à 8 h (GitHub espaçait la tâche planifiée). Ajout de la tâche `Horloge` qui la relance toutes les 10 min. Écran des pièces : tuile « Dehors » (sonde extérieure de la station du salon) à gauche du Salon, avec sa propre échelle (Gel < 0 °C, Froid < 10, Doux < 25, Chaud < 30, Canicule au-delà) ; le Salon prend désormais une seule case, pour garder 8 tuiles sur 2 rangées. La tuile Dehors affiche aussi en haut à droite le pictogramme du temps actuel et celui de 12 h (Open-Meteo, code météo horaire) ; après 13 h, c'est celui du lendemain midi (« dem. 12 h »).
- **5 nov. 2026 (appli)** : la météo seule devient installable sur iPhone et Android (icône soleil et nuage, plein écran), pour la partager à la famille. Publication sur l'App Store et Google Play mise de côté (voir le document du projet « Apps iOS et Android — à reprendre »).
- **5 nov. 2026 (chauffage)** : lecture du radiateur Carrera de la SdB filles (« SDB2 » dans Home-SmartLink, n° 7) par la tâche, en lecture seule (secrets `HSL_EMAIL`, `HSL_MOT_DE_PASSE`) ; la tuile SdB filles affiche son mode et sa consigne (`radiateur: 7` dans `CAPTEURS`), masqués si `chauffage.json` a plus d'une heure. Page Chauffage (`chauffage.html`) avec les réglages : la page envoie la demande à la tâche « Régler le chauffage » avec un jeton GitHub à granularité fine (dépôt Maison17 seul, permission Actions en lecture et écriture), saisi une fois sur chaque appareil autorisé et gardé dans son navigateur ; le raccourci 🔥 Chauffage n'apparaît que sur ces appareils. Si le jeton expire, la page le signale : en créer un nouveau et le recoller. La page montre aussi la programmation de la semaine (barres confort par jour) et permet de modifier les 6 plages de la programmation avancée (jours cochés, début et fin par pas de 10 min, sans passer minuit ; aucun jour = plage inactive). Hors des plages, le radiateur est en éco. Depuis le 5 nov. 2026 (13 h 30), la température relevée par le radiateur et sa consigne sont enregistrées à chaque publication dans `historique/chauffage-AAAA-MM.csv` (`horodatage` du relevé par la box, `piece`, `temperature`, `consigne`, `mode`) ; la page Chauffage en trace la courbe (24 h ou 7 jours) avec celle du capteur Mobile Alerts de la pièce.
- **À reprendre** : alertes automatiques (pile faible, box du chauffage hors ligne, capteur muet) envoyées par la tâche, par notification ntfy, e-mail, WhatsApp (CallMeBot) ou SMS (Free Mobile) ; pour les mesures figées, veilleur extérieur gratuit (healthchecks.io) prévenu à chaque passage.
- Idées écartées pour l'instant : appli Apple TV native (nécessite un Mac), intégration de SmartThings.
