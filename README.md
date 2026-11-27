# Météo Alertes Belgique

La recherche propose des localités belges dès la saisie d’un nom ou d’un code postal. Frasnes-lez-Gosselies s’affiche au démarrage. Les échéances sont en heure belge.

- La carte d’accueil combine AROME HD, ICON-D2, ECMWF IFS et ICON Global pour la température et le ressenti. L’icône et le descriptif s’appuient sur AROME HD et ICON-D2 ou sur une observation METAR exploitable datant de 75 minutes au plus et située à 15 km au plus. Une observation est identifiée par sa station et son heure.
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
