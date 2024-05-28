from flask import Flask, redirect, request, session, url_for, render_template, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CLIENT_ID = '127378d20985402b80e14553fd1368e7'
CLIENT_SECRET = '51d1b4df28e64fd8b2a67164fa62f914'
REDIRECT_URI = 'http://localhost:5000/callback'

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope='user-library-read playlist-read-private playlist-modify-public playlist-modify-private')

# SQLite Database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, spotify_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, id_, username, spotify_id):
        self.id = id_
        self.username = username
        self.spotify_id = spotify_id

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        if not user:
            return None
        return User(id_=user[0], username=user[1], spotify_id=user[3])

    @staticmethod
    def find_by_spotify_id(spotify_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE spotify_id = ?', (spotify_id,))
        user = c.fetchone()
        conn.close()
        if not user:
            return None
        return User(id_=user[0], username=user[1], spotify_id=user[3])

    @staticmethod
    def create(username, password, spotify_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, spotify_id) VALUES (?, ?, ?)', (username, generate_password_hash(password), spotify_id))
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            user_obj = User(id_=user[0], username=user[1], spotify_id=user[3])
            login_user(user_obj)
            flash('Logged in successfully.')
            return redirect(url_for('display_playlists'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        User.create(username, password, None)  # Create user without spotify_id initially
        flash('Account created successfully. Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

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

    flash(f"Spotify ID retrieved: {spotify_id}")

    if current_user.is_authenticated:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('UPDATE users SET spotify_id = ? WHERE id = ?', (spotify_id, current_user.id))
        conn.commit()
        conn.close()
        flash('Spotify account linked successfully.')
        return redirect(url_for('display_playlists'))
    else:
        flash('Please log in or sign up to link your Spotify account.')
        return redirect(url_for('login'))


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
    current_user_info = sp.current_user()
    user_id = current_user_info['id']
    playlists = sp.current_user_playlists()
    structured_playlists = [
        {
            'name': playlist['name'],
            'id': playlist['id'],
            'total_tracks': playlist['tracks']['total'],
            'external_url': playlist['external_urls']['spotify'],
            'image_url': playlist['images'][0]['url'] if playlist['images'] else None,
            'owner_id': playlist['owner']['id'],
            'created_by_user': playlist['owner']['id'] == user_id
        } for playlist in playlists['items']
    ]
    return render_template('playlists.html', playlists=structured_playlists, user_id=user_id)

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
    else:
        spotify_id = "Not Linked"
        flash("Spotify ID not linked")

    return render_template('profile.html', spotify_id=spotify_id)


if __name__ == '__main__':
    app.run(debug=True)