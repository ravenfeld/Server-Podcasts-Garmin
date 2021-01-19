#! /Library/Frameworks/Python.framework/Versions/3.8/bin/python3.8
# -*- coding: utf-8 -*-
from flask import request
from flask import Flask
from flask import render_template
from flask import send_from_directory
from flask import Response
from flask import redirect
from flask import session
from flask_accept import accept
from flask_caching import Cache
from functools import wraps
import os
import threading
import json
import manager_podcast
import api_podcasting_index
import config


configuration_flask = {
    "CACHE_TYPE": "simple",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}

lock = threading.Lock()
app = Flask(__name__)
app.secret_key = 'ed9e80f235a0c0ea6d945efc87f16c88e4a6b47a'
app.config.from_mapping(configuration_flask)
cache = Cache(app)


@app.before_first_request
def before_first_request():
    if config.ACTIVE_LOG:
        print("before_first_request")
    manager_podcast.create_database()
    manager_podcast.check_new_episodes()


def require_user_id(func):
    @wraps(func)
    def check_token(*args, **kwargs):
        user_id = None
        if(request.headers.get('Authorization') != None):
            user_id = manager_podcast.user_id(
                request.headers.get('Authorization'))
        elif 'session_token' in session:
            user_id = manager_podcast.user_id(session['session_token'])

        if user_id != None:
            kwargs['user_id'] = user_id
            return func(*args, **kwargs)
        else:
            if(request.headers.get("Accept") == 'application/json'):
                return Response(json.dumps({'error': 'Access denied'}), status=401, mimetype='application/json')
            else:
                return redirect("/login")
    return check_token


@app.route('/podcast/search', methods=['GET'])
@accept('application/json')
@require_user_id
@cache.cached(timeout=86400, query_string=True)
def get_search_podcast(user_id):
    name = request.values.get("name")
    if config.ACTIVE_LOG:
        print("name : "+str(name))
    if(name is None):
        return Response(json.dumps({'error': 'missing parameter'}), status=400, mimetype='application/json')
    elif os.environ['PODCASTING_INDEX_KEY'] in (None, ''):
        return Response(json.dumps({'error': 'missing API KEY'}), status=401, mimetype='application/json')
    else:
        return Response(json.dumps(api_podcasting_index.search_podcats(name)), status=200, mimetype='application/json')


@app.route('/podcast/add', methods=['POST'])
@require_user_id
def post_add_podcast_rss(user_id):
    rss_url = request.values.get("rss")
    if config.ACTIVE_LOG:
        print("rss_url : "+str(rss_url))
    if(rss_url is not None):
        if(manager_podcast.add_podcast_rss(user_id=user_id, rss_url=rss_url).code == manager_podcast.StatusCode.OK):
            return Response(json.dumps({}), status=200, mimetype='application/json')
        else:
            return Response(json.dumps({'error': 'unable to add url'}), status=404, mimetype='application/json')
    else:
        return Response(json.dumps({'error': 'many parameter'}), status=400, mimetype='application/json')


@app.route('/podcast/<int:id_podcast>/remove', methods=['POST'])
@require_user_id
def post_remove_podcast(user_id, id_podcast):
    return Response(json.dumps(manager_podcast.remove_podcast(user_id, id_podcast)), status=200, mimetype='application/json')


@app.route('/podcast', methods=['GET'])
@accept('application/json')
@require_user_id
def get_list_podcast(user_id):
    return Response(json.dumps(manager_podcast.list_podcast(user_id=user_id)), status=200, mimetype='application/json')


@app.route('/podcast/<int:podcast_id>', methods=['GET'])
@accept('application/json')
@require_user_id
def get_podcast(user_id, podcast_id):
    podcast = manager_podcast.podcast(user_id, podcast_id)
    return Response(json.dumps(podcast), status=200, mimetype='application/json')


@app.route('/episode/readed', methods=['POST'])
@require_user_id
def post_readed_episode(user_id):
    ids = request.values.get("ids")
    if config.ACTIVE_LOG:
        print("ids : "+str(ids))
    if(ids is None):
        return Response(json.dumps({'error': 'missing parameter'}), status=400, mimetype='application/json')
    else:
        return Response(json.dumps(manager_podcast.readed_episodes(user_id, ids)), status=200, mimetype='application/json')


@app.route('/episode/not_readed', methods=['POST'])
@require_user_id
def post_not_readed_episode(user_id):
    ids = request.values.get("ids")
    if config.ACTIVE_LOG:
        print("ids : "+str(ids))
    if(ids is None):
        return Response(json.dumps({'error': 'missing parameter'}), status=400, mimetype='application/json')
    else:
        return Response(json.dumps(manager_podcast.not_readed_episodes(user_id, ids)), status=200, mimetype='application/json')


@app.route('/episode/sync_watch', methods=['POST'])
@require_user_id
def post_sync_watch_episode(user_id):
    ids = request.values.get("ids")
    if config.ACTIVE_LOG:
        print("ids : "+str(ids))
    if(ids is None):
        return Response(json.dumps({'error': 'missing parameter'}), status=400, mimetype='application/json')
    else:
        return Response(json.dumps(manager_podcast.sync_watch_episodes(user_id, ids)), status=200, mimetype='application/json')


@app.route('/episode/not_sync_watch', methods=['POST'])
@require_user_id
def post_not_sync_watch_episode(user_id):
    ids = request.values.get("ids")
    if config.ACTIVE_LOG:
        print("ids : "+str(ids))
    if(ids is None):
        return Response(json.dumps({'error': 'missing parameter'}), status=400, mimetype='application/json')
    else:
        return Response(json.dumps(manager_podcast.not_sync_watch_episodes(user_id, ids)), status=200, mimetype='application/json')


@app.route('/watch/sync', methods=['GET'])
@accept('application/json')
@require_user_id
def get_list_episode_sync_watch(user_id):
    remove_readed = request.values.get("remove_readed")
    if config.ACTIVE_LOG:
        print("remove_readed : "+str(remove_readed))
    return Response(json.dumps(manager_podcast.list_episode_sync_watch(user_id, remove_readed)), status=200, mimetype='application/json')


@app.route('/create_user', methods=['POST'])
@accept('application/json')
def create_user():
    login = request.form.get('login')
    password = request.form.get('password')
    result = manager_podcast.create_account(login, password)
    if result.code == manager_podcast.StatusCode.ERROR:
        return Response(json.dumps({'error': result.data}), status=403, mimetype='application/json')
    else:
        session['session_token'] = result.data
        return Response(json.dumps({"token": result.data}), status=200, mimetype='application/json')


@app.route('/create_user', methods=['GET'])
@accept('text/html')
def web_ui_create_user():
    return render_template("create_user.html")


@app.route('/login', methods=['GET'])
@accept('text/html')
def web_ui_login():
    return render_template("login.html")


@app.route('/logout', methods=['GET'])
@accept('text/html')
def web_ui_logout():
    session.clear()
    return render_template("login.html")


@app.route('/connect', methods=['POST'])
@accept('application/json')
def connect():
    login = request.form.get('login')
    password = request.form.get('password')
    response = manager_podcast.token(login, password)
    if response.code == manager_podcast.StatusCode.OK:
        session['session_token'] = response.data
        return Response(json.dumps({"token": response.data}), status=200, mimetype='application/json')
    else:
        return Response(json.dumps({"error": response.data}), status=403, mimetype='application/json')


@app.route('/', methods=['GET'])
@accept('text/html')
@require_user_id
def web_ui_index(user_id):
    podcasts = manager_podcast.list_podcast(user_id=user_id, no_episodes=True)
    return render_template("index.html", podcasts=podcasts)


@app.route('/podcast/add', methods=['GET'])
@accept('text/html')
@require_user_id
def web_ui_podcast_add(user_id):
    return render_template("podcast-add.html")


@get_podcast.support('text/html')
@require_user_id
def web_ui_podcast(user_id, podcast_id):
    podcast = manager_podcast.podcast(user_id=user_id, podcast_id=podcast_id)
    return render_template("podcast-id.html", podcast=podcast)


@app.route('/check_new_episodes', methods=['POST'])
@require_user_id
def check_new_episodes(user_id):
    manager_podcast.check_new_episodes(0)
    return Response(json.dumps({}), status=200, mimetype='application/json')


if __name__ == '__main__':
    port = os.getenv('PORT', '5000')
    app.run(debug=config.ACTIVE_LOG, use_reloader=True, host='0.0.0.0', port=port)
