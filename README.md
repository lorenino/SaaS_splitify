# SaaS_splitify

SaaS_splitify est une application web utilisant Flask et Spotify API pour gérer et manipuler les playlists Spotify. Les utilisateurs peuvent se connecter via Spotify, visualiser et gérer leurs playlists, et interagir avec les pistes des playlists.

## Fonctionnalités

- **Connexion Spotify** : Authentification via Spotify OAuth.
- **Gestion des utilisateurs** : Création et gestion des utilisateurs avec SQLite.
- **Visualisation des playlists** : Afficher les playlists et les pistes de l'utilisateur.
- **Manipulation des pistes** : Ajouter ou supprimer des pistes des playlists.

## Installation

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/lorenino/SaaS_splitify.git
   ```
2. Naviguez dans le répertoire du projet :
   ```bash
   cd SaaS_splitify
   ```
3. Installez les dépendances requises :
   ```bash
   pip install -r requirements.txt
   ```
4. Configurez les identifiants Spotify :
   Modifiez les variables `CLIENT_ID`, `CLIENT_SECRET`, et `REDIRECT_URI` dans le fichier principal.

## Utilisation

1. Initialisez la base de données :
   ```bash
   python -c 'from main import init_db; init_db()'
   ```
2. Lancez l'application :
   ```bash
   python main.py
   ```
3. Ouvrez votre navigateur et accédez à `http://localhost:5000`.

## Routes principales

- `/` : Page d'accueil
- `/about` : Page à propos
- `/spotify_login` : Connexion via Spotify
- `/callback` : Callback de Spotify OAuth
- `/display_playlists` : Affichage des playlists de l'utilisateur
- `/playlist/<playlist_id>` : Affichage des détails d'une playlist
- `/select_playlists/<playlist_id>` : Sélectionner des playlists pour l'ajout de pistes
- `/playlist/<playlist_id>/swipe` : Swipe des pistes d'une playlist
- `/playlist/<playlist_id>/swipe_with_add` : Swipe des pistes avec ajout à d'autres playlists
- `/logout` : Déconnexion
- `/profile` : Afficher le profil de l'utilisateur

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus d'informations.

---
