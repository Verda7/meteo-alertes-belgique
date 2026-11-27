# Météo Alertes Belgique

La recherche propose des localités belges dès la saisie d’un nom ou d’un code postal. Frasnes-lez-Gosselies s’affiche au démarrage. Les échéances sont en heure belge.

- Le bandeau affiche les derniers relevés de la station de Rèves pour Rèves, Frasnes-lez-Gosselies et Les Bons Villers. Le ressenti provient de la station, ou est calculé avec son vent et son humidité. Si le vent de Rèves manque, un relevé récent et proche dans le temps du vent à Charleroi (EBCI) peut être utilisé avec la température et l’humidité de Rèves. En dernier recours, le ressenti des modèles est identifié comme une estimation locale. Pour les autres localités, ou si Rèves est indisponible, le bandeau choisit la station la plus proche parmi les réseaux meteo-be.net et METAR avec une mesure de moins de 45 minutes dans un rayon de 15 km. Sans mesure à proximité, il affiche une estimation pour l’heure en cours. L’icône et le descriptif s’appuient sur AROME HD et ICON-D2 ou sur une observation METAR exploitable datant de 75 minutes au plus et située à 15 km au plus. Une observation est identifiée par sa station et son heure.
- Le résumé et les graphiques sur sept jours combinent AROME HD, ICON-D2, ICON-EU et ECMWF IFS. Les moyennes utilisent les valeurs disponibles pour chaque variable et chaque heure. Les durées et cumuls quotidiens exigent une série horaire complète.
- Le radar affiche la page de l’IRM et permet de l’ouvrir directement.
- Le bulletin et la vigilance locale analysent les signaux détectés à la localité choisie sur 24 ou 48 heures. Le bulletin est consultable et téléchargeable en TXT. Les avertissements officiels figurent dans l’onglet Alertes IRM.

## Streamlit Community Cloud

Décompresser le ZIP et déposer les fichiers à la racine du dépôt GitHub de Météo Alertes Belgique. Le fichier d’entrée est `app.py`. Les fichiers `app.py`, `weekly.py` et `observations.py` doivent être mis à jour ensemble. Les fonctionnalités de cette version utilisent les sources publiques et ne nécessitent pas de configuration de secret.

## Lancer en local

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
