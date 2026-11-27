# Météo Alertes · Belgique

Prévisions sur 24 h et 48 h en heure belge. Frasnes-lez-Gosselies est la localité par défaut. Saisis un nom ou un code postal belge, clique sur **Rechercher**, puis choisis la localité dans **Localité surveillée**.

## Lancer sur Windows

Décompresse le ZIP, puis ouvre un terminal dans le dossier contenant `app.py`. Avec Python 3.11 ou 3.12 installé, exécute ces commandes dans PowerShell.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Ouvre http://localhost:8501 si le navigateur ne s’ouvre pas automatiquement.

Sur macOS ou Linux, utilise `python3 -m venv .venv`, puis `./.venv/bin/python` à la place de `.\.venv\Scripts\python.exe`.

## Utiliser sur Streamlit Cloud

Place les fichiers extraits à la racine d’un nouveau dépôt GitHub. Dans Streamlit Community Cloud, crée une nouvelle application à partir de ce dépôt, avec `app.py` comme fichier d’entrée. Pour une nouvelle application, ajoute `KACHELMANN_API_KEY` dans **Settings → Secrets** si tu souhaites activer Meteologix.

## Activer Meteologix en local

Copie `.streamlit/secrets.toml.example` en `.streamlit/secrets.toml`, puis renseigne ta clé dans ce fichier local. Les cinq modèles Open-Meteo fonctionnent sans clé. Meteologix fournit jusqu’à 24 échéances et le flux testé ne précise pas le modèle d’origine.

## Choisir les courbes

Dans **Graphiques**, choisis les modèles dans **Modèles à afficher**, puis le paramètre. La moyenne calcule chaque point avec les valeurs disponibles pour les modèles affichés. Le choix des courbes est indépendant des sources utilisées pour la vigilance et le tableau des précipitations, que tu peux régler dans **Modèles et méthode de calcul**.

Dans les cartes **Gel de l’air** et **Gel au sol**, les seuils sont 0 °C (faible), −5 °C (modéré), −10 °C (fort) et −15 °C (sévère), selon les valeurs brutes.

À l’ouverture, la synthèse utilise la méthode **Prudente**. Dans **Graphiques**, la moyenne horaire apparaît en blanc pointillé sur fond sombre. La légende est sous le graphique et la mention « Heure belge » au-dessus.

## Préparer un bulletin d’avertissements

L’onglet **Bulletin** prépare un texte pour la localité sélectionnée et ses environs sur l’horizon choisi. Le bulletin résume les risques détectés en texte continu. Le niveau est précisé pour le gel de l’air et le gel au sol. Tu peux modifier le texte, le copier dans ta publication ou le télécharger en TXT.

## Consulter les avertissements IRM

L’onglet **Alertes IRM** affiche, pour chacune des dix zones, le code maximal annoncé sur la période choisie (24 h ou 48 h). Le menu **Zone à consulter** affiche le détail de la zone sélectionnée. La zone correspondant à la localité est présélectionnée quand sa province est reconnue. La zone côtière reste accessible dans le menu. Les horaires sont en heure belge.

© 2026 David Vergucht
