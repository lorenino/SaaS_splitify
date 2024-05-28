from flask import Flask, redirect, request, session, url_for, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

CLIENT_ID = '127378d20985402b80e14553fd1368e7'
CLIENT_SECRET = '51d1b4df28e64fd8b2a67164fa62f914'
REDIRECT_URI = 'http://localhost:5000/callback'

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope='user-library-read playlist-read-private playlist-modify-public playlist-modify-private')

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('display_playlists'))

@app.route('/display_playlists')
def display_playlists():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    sp = Spotify(auth=token_info['access_token'])
    current_user = sp.current_user()
    user_id = current_user['id']
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
def view_playlist(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    return render_template('playlist_details.html', playlist=playlist)

@app.route('/select_playlists/<playlist_id>', methods=['GET', 'POST'])
def select_playlists(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

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
def swipe_playlist(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    tracks = playlist['tracks']['items']
    return render_template('swipe.html', tracks=tracks, playlist_id=playlist_id, selected_playlists=[])

@app.route('/playlist/<playlist_id>/swipe_with_add')
def swipe_playlist_with_add(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    selected_playlists = request.args.get('selected_playlists', '').split(',')
    sp = Spotify(auth=token_info['access_token'])
    playlist = sp.playlist(playlist_id)
    tracks = playlist['tracks']['items']
    return render_template('swipe.html', tracks=tracks, playlist_id=playlist_id, selected_playlists=selected_playlists)

@app.route('/playlist/<playlist_id>/remove_track/<track_id>', methods=['POST'])
def remove_track(playlist_id, track_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    sp = Spotify(auth=token_info['access_token'])
    sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
    return '', 204

@app.route('/playlist/<playlist_id>/add_track_to_playlists/<track_id>', methods=['POST'])
def add_track_to_playlists(playlist_id, track_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    selected_playlists = request.json.get('selected_playlists', [])
    sp = Spotify(auth=token_info['access_token'])
    for pl_id in selected_playlists:
        sp.playlist_add_items(pl_id, [track_id])
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)