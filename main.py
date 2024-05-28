from flask import Flask, redirect, request, session, url_for, render_template, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'spotify_login'

CLIENT_ID = '127378d20985402b80e14553fd1368e7'
CLIENT_SECRET = '51d1b4df28e64fd8b2a67164fa62f914'
REDIRECT_URI = 'http://localhost:5000/callback'

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope='user-library-read playlist-read-private playlist-modify-public playlist-modify-private')

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        spotify_id TEXT UNIQUE,
        email TEXT UNIQUE
    )
    ''')
    conn.commit()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, id_, username, spotify_id, email):
        self.id = id_
        self.username = username
        self.spotify_id = spotify_id
        self.email = email

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        if not user:
            return None
        return User(id_=user[0], username=user[1], spotify_id=user[2], email=user[3])

    @staticmethod
    def find_by_spotify_id(spotify_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE spotify_id = ?', (spotify_id,))
        user = c.fetchone()
        conn.close()
        if not user:
            return None
        return User(id_=user[0], username=user[1], spotify_id=user[2], email=user[3])

    @staticmethod
    def create(username, spotify_id, email):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, spotify_id, email) VALUES (?, ?, ?)', (username, spotify_id, email))
        conn.commit()
        conn.close()

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/spotify_login')
def spotify_login():
    return redirect(sp_oauth.get_authorize_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    sp = Spotify(auth=token_info['access_token'])
    user_info = sp.current_user()
    spotify_id = user_info['id']
    email = user_info['email']
    username = user_info['display_name'] or user_info['id']

    # Vérifiez si l'utilisateur est connecté
    user = User.find_by_spotify_id(spotify_id)
    if user:
        login_user(user)
        flash('Logged in with Spotify successfully.')
    else:
        # Si l'utilisateur n'existe pas, créez-en un nouveau
        User.create(username, spotify_id, email)
        user = User.find_by_spotify_id(spotify_id)
        login_user(user)
        flash('Account created and logged in with Spotify successfully.')

    return redirect(url_for('display_playlists'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/display_playlists')
@login_required
def display_playlists():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    sp = Spotify(auth=token_info['access_token'])
    user_playlists = sp.current_user_playlists()
    user_id = sp.current_user()['id']
    playlists = [
        {
            'name': playlist['name'],
            'id': playlist['id'],
            'total_tracks': playlist['tracks']['total'],
            'external_url': playlist['external_urls']['spotify'],
            'image_url': playlist['images'][0]['url'] if playlist['images'] else None,
            'owner_id': playlist['owner']['id'],
            'created_by_user': playlist['owner']['id'] == user_id
        } for playlist in user_playlists['items']
    ]

    return render_template('playlists.html', playlists=playlists, user_id=user_id)

@app.route('/playlist/<playlist_id>')
@login_required
def view_playlist(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    return render_template('playlist_details.html', playlist=playlist)

@app.route('/select_playlists/<playlist_id>', methods=['GET', 'POST'])
@login_required
def select_playlists(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    sp = Spotify(auth=token_info['access_token'])
    if request.method == 'POST':
        selected_playlists = request.form.getlist('selected_playlists')
        return redirect(url_for('swipe_playlist_with_add', playlist_id=playlist_id, selected_playlists=','.join(selected_playlists)))

    playlists = sp.current_user_playlists()
    structured_playlists = [
        {
            'name': playlist['name'],
            'id': playlist['id'],
            'image_url': playlist['images'][0]['url'] if playlist['images'] else None
        } for playlist in playlists['items'] if playlist['owner']['id'] == sp.current_user()['id']
    ]
    return render_template('select_playlists.html', playlists=structured_playlists, current_playlist_id=playlist_id)

@app.route('/playlist/<playlist_id>/swipe')
@login_required
def swipe_playlist(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    tracks = playlist['tracks']['items']
    return render_template('swipe.html', tracks=tracks, playlist_id=playlist_id, selected_playlists=[])

@app.route('/playlist/<playlist_id>/swipe_with_add')
@login_required
def swipe_playlist_with_add(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    selected_playlists = request.args.get('selected_playlists', '').split(',')
    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    tracks = playlist['tracks']['items']
    
    # Get details of the selected playlists
    playlists = sp.current_user_playlists()
    selected_playlists_details = [
        {
            'name': playlist['name'],
            'id': playlist['id'],
            'image_url': playlist['images'][0]['url'] if playlist['images'] else None
        } for playlist in playlists['items'] if playlist['id'] in selected_playlists
    ]
    
    return render_template('swipe.html', tracks=tracks, playlist_id=playlist_id, selected_playlists=selected_playlists_details)

@app.route('/playlist/<playlist_id>/remove_track/<track_id>', methods=['POST'])
@login_required
def remove_track(playlist_id, track_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    sp = Spotify(auth=token_info['access_token'])
    sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
    return '', 204

@app.route('/playlist/<playlist_id>/add_track_to_playlists/<track_id>', methods=['POST'])
@login_required
def add_track_to_playlists(playlist_id, track_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('spotify_login'))

    selected_playlists = request.json.get('selected_playlists', [])
    sp = Spotify(auth=token_info['access_token'])
    for pl_id in selected_playlists:
        sp.playlist_add_items(pl_id, [track_id])
    return '', 204

@app.route('/profile')
@login_required
def profile():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT spotify_id FROM users WHERE id = ?', (current_user.id,))
    spotify_id = c.fetchone()
    conn.close()

    if spotify_id:
        spotify_id = spotify_id[0]
        sp = get_spotify_client()
        user_info = sp.current_user()
        profile_info = {
            'display_name': user_info.get('display_name', 'N/A'),
            'email': user_info.get('email', 'N/A'),
            'followers': user_info.get('followers', {}).get('total', 'N/A'),
            'profile_image': user_info.get('images', [{}])[0].get('url', None)
        }
    else:
        spotify_id = "Not Linked"
        profile_info = {}
        flash("Spotify ID not linked")

    return render_template('profile.html', spotify_id=spotify_id, profile_info=profile_info)


def get_spotify_client():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    
    return Spotify(auth=token_info['access_token'])

@app.route('/spotify_login_direct')
def spotify_login_direct():
    return redirect(sp_oauth.get_authorize_url())

if __name__ == '__main__':
    app.run(debug=True)
