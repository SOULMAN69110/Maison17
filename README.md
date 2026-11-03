# Météo-maison17

Tableau de bord de la maison (69110, Sainte-Foy-lès-Lyon), affiché sur la télé Samsung via l'Apple TV. Il réunit les capteurs Mobile Alerts et la météo, et garde l'historique des mesures.

Mis en place le 3 novembre 2026.

## Adresses

| Page | Adresse |
|---|---|
| Tableau de bord (télé) | https://soulman69110.github.io/Maison17/ |
| Courbes et historique | https://soulman69110.github.io/Maison17/historique.html |
| Mesures brutes (CSV) | dossier [`historique/`](historique/) de ce dépôt |

**Affichage sur la télé** : ouvrir le tableau de bord dans Safari sur l'iPhone, tourner le téléphone à l'horizontale, puis centre de contrôle → Recopie de l'écran → Apple TV. La page s'ouvre aussi directement dans le navigateur de la télé Samsung.

## Capteurs Mobile Alerts

| Pièce | Identifiant | Mesures |
|---|---|---|
| Salon (station) | salon | température et humidité intérieures et extérieures |
| Chambre Claire | chambre-c | température, humidité |
| Chambre parents | chambre-parents | température, humidité |
| Chambre Yaël | chambre-y | température, humidité |
| Bureau | bureau | température, humidité |
| SdB filles | sdb-filles | température |
| SdB parents | sdb-parents | température |

La pression et le pictogramme de prévision de la station du salon ne sont pas transmis par Mobile Alerts : ils viennent d'Open-Meteo (gratuit, sans clé), pour la position de Sainte-Foy-lès-Lyon.

## Fonctionnement

1. Toutes les 10 minutes environ (souvent avec un peu de retard), la tâche GitHub Actions `Mesures et publication` interroge Mobile Alerts et Open-Meteo.
2. Elle ajoute les nouvelles mesures aux fichiers mensuels `historique/mesures-AAAA-MM.csv` et `historique/pression-AAAA-MM.csv`, et les enregistre dans le dépôt.
3. Elle republie le site sur GitHub Pages avec une copie des dernières mesures (`data.json`).

Mobile Alerts refuse les appels directs depuis un navigateur : c'est pour ça que la page lit la copie publiée par la tâche, et non l'API elle-même. La météo (prévisions et pression affichées) est en revanche lue en direct par la page.

### Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | tableau de bord ; noms et ordre des pièces en tête du script |
| `historique.html` | page de courbes (24 h, 7 jours, 30 jours, 1 an) |
| `outils/historiser.py` | ajoute les mesures aux CSV sans doublons |
| `.github/workflows/pages.yml` | la tâche automatique ; liste des identifiants à mettre à jour si on ajoute un capteur |

### Format des CSV

- `mesures-AAAA-MM.csv` : `horodatage` (secondes Unix), `capteur`, `temp`, `hum`, `temp_ext`, `hum_ext` (les deux dernières pour la station du salon)
- `pression-AAAA-MM.csv` : `horodatage`, `pression_hpa`

## Entretien

- **Si les chiffres se figent** : GitHub met en pause les tâches planifiées d'un dépôt public après 60 jours sans activité. Les enregistrements d'historique comptent normalement comme activité ; sinon, relancer la tâche depuis l'onglet Actions (*Run workflow*).
- **Ajouter un capteur** : l'ajouter dans `CAPTEURS` dans `index.html` et `historique.html`, et dans `IDS` dans `pages.yml`.
- **Piles faibles** au 3 novembre 2026 : Chambre parents, Chambre Yaël, SdB parents.

## Historique du projet

- **3 nov. 2026** : création du tableau de bord (heure, extérieur, 7 pièces avec confort, humidité et alertes de pile), hébergement sur GitHub Pages, ajout de la pression et des prévisions sur 4 jours, démarrage de l'historique des mesures et de la page de courbes.
- Idées écartées pour l'instant : appli Apple TV native (nécessite un Mac), intégration de SmartThings.
