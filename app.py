from flask import Flask, render_template, request, url_for
import requests
import urllib.parse
import json
import threading
from datetime import datetime

app = Flask(__name__)

PLAYER_MAP = {
    "38482907203152": "YF",
    "38482907326032": "Levi",
    "38482907259824": "Focus",
    "38482907077376": "Nina",
    "38482907240208": "HoneyBee",
    "38482907135216":"OzzieNinja",
    "38482907334784": "KEI/Sonu",
    "38482906974768": "NIK",
    "38482907346800": "Fury",
    "38482907153024": "SG[INV]"
}

access_token_cache = {
    "token": None,
    "lock": threading.Lock()
}

def request_new_access_token():
    auth_url = 'https://eur-janus.gameloft.com/authorize'
    form_data = {
        'client_id': 'gah:1867:69703:9.0.0c:steam:steam',
        'username': 'anonymous:d2luMzJfc3RlYW1fNzY1NjExOTg4MzA3ODk3MzFfMTc0NjE5NDE4Nl+m3bRSBks4EoTGkY53wg1L',
        'password': 'Y1Yh5y0KyWgXTZCh',
        'scope': 'auth chat config leaderboard_ro lobby message social storage translation',
        'device_id': '389714701901586724',
        'for_credential_type': 'anonymous'
    }

    response = requests.post(auth_url, data=form_data)
    response.raise_for_status()
    token_data = response.json()
    return token_data['access_token']

def get_cached_access_token():
    with access_token_cache["lock"]:
        if access_token_cache["token"] is None:
            access_token_cache["token"] = request_new_access_token()
        return access_token_cache["token"]

def update_cached_access_token():
    with access_token_cache["lock"]:
        access_token_cache["token"] = request_new_access_token()
        return access_token_cache["token"]

def fetch_mail(player_id, token):
    encoded_token = urllib.parse.quote(token, safe='')
    get_url = f"https://eur-osiris.gameloft.com/game_objects/sent_wall_{player_id}/wall?access_token={encoded_token}&language=json&limit=100&expiration=30"
    response = requests.get(get_url)
    if response.status_code == 401:
        # Token expired; refresh and retry
        token = update_cached_access_token()
        encoded_token = urllib.parse.quote(token, safe='')
        get_url = f"https://eur-osiris.gameloft.com/game_objects/sent_wall_{player_id}/wall?access_token={encoded_token}&language=json&limit=100&expiration=30"
        response = requests.get(get_url)
    response.raise_for_status()
    return response.json()

@app.route('/', methods=['GET', 'POST'])
def index():
    mails = []
    error = None
    selected_player = None

    if request.method == 'POST':
        selected_player = request.form.get('player_id')
        force_refresh = request.form.get('refresh') == '1'

        if selected_player not in PLAYER_MAP:
            error = "Invalid player selected."
        else:
            try:
                token = get_cached_access_token() if not force_refresh else update_cached_access_token()
                mail_data = fetch_mail(selected_player, token)

                for mail in mail_data:
                    mail_json_str = mail.get('text', '{}')
                    creation_str = mail.get('creation', '')
                    date_str, time_str = '', ''
                    if creation_str:
                        try:
                            creation_dt = datetime.strptime(creation_str, '%Y-%m-%d %H:%M:%SZ')
                            date_str = creation_dt.strftime('%Y-%m-%d')
                            time_str = creation_dt.strftime('%H:%M:%S')
                        except:
                            date_str = creation_str

                    try:
                        parsed_mail = json.loads(mail_json_str)
                    except json.JSONDecodeError:
                        parsed_mail = {}

                    user_mail = parsed_mail.get('user_mail', {})
                    text = user_mail.get('text', '')
                    subject = user_mail.get('subject', '')
                    sender_name = user_mail.get('sender_name', '')

                    display_text = text
                    if text:
                        try:
                            text_parsed = json.loads(text)
                            if isinstance(text_parsed, dict) and 'IsWinner' in text_parsed:
                                display_text = "Battle won" if text_parsed.get('IsWinner') else "Battle lost"
                        except json.JSONDecodeError:
                            pass

                    mails.append({
                        'sender_name': sender_name,
                        'subject': subject,
                        'text': display_text,
                        'date': date_str,
                        'time': time_str
                    })

            except Exception as e:
                error = str(e)
    bg_url = url_for('static', filename='images/bg.jpg')
    return render_template('index.html',bg_url=bg_url,
                           mails=mails,
                           players=PLAYER_MAP,
                           error=error,
                           selected_player=selected_player)

if __name__ == '__main__':
    app.run(debug=True)
