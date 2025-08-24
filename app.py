#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
#  filename:   /home/al/projects/audio-player/app.py
#
#  Copyright 2025 AL Haines
# you will need fix paths to match your needs 
# this is an example only not for actual use!

from flask import Flask, render_template, send_file, jsonify, request
import os
import re
from MySql import MySQL
import config_audio

app = Flask(__name__)
app.secret_key = os.urandom(24)
db = MySQL(**config_audio.mysql_config)

def _get_item_details(table_name, item_id):
    query = f"SELECT * FROM `{table_name}` WHERE id = %s"
    results = db.get_data(query, (item_id,))
    return results[0] if results else None

@app.route('/')
def index():
    all_tables_raw = db.get_data("SHOW TABLES")
    if not all_tables_raw:
        return render_template('index.html', categories=[], resume_items=[])

    all_tables = [list(t.values())[0] for t in all_tables_raw]
    longform_tables = [t for t in all_tables if t in ['audio_audiobooks', 'audio_instructional', 'audio_comedy']]

    union_queries = []
    for table in all_tables:
        columns = db.get_field_names(table)
        if 'resume_position' in columns and 'last_played' in columns:
            union_queries.append(f"(SELECT id, album, title, '{table}' as category, last_played, resume_position FROM `{table}` WHERE resume_position > 0.1)")

    resume_items = []
    if union_queries:
        resume_query = " UNION ALL ".join(union_queries) + " ORDER BY last_played DESC LIMIT 10"
        resume_items = db.get_data(resume_query)

    return render_template('index.html', categories=longform_tables, resume_items=resume_items)

@app.route('/get_albums/<string:category_name>')
def get_albums(category_name):
    query = f"SELECT DISTINCT album FROM `{category_name}` WHERE album IS NOT NULL ORDER BY album ASC"
    results = db.get_data(query)
    albums = [row['album'] for row in results] if results else []
    return jsonify(albums)

@app.route('/get_tracks/<string:category_name>/<string:album_name>')
def get_tracks(category_name, album_name):
    query = f"SELECT id, title FROM `{category_name}` WHERE album = %s ORDER BY track_number, title ASC"
    tracks = db.get_data(query, (album_name,))
    return jsonify(tracks if tracks else [])

@app.route('/play/<string:table_name>/<int:item_id>')
def player(table_name, item_id):
    current_item = _get_item_details(table_name, item_id)
    if not current_item:
        return "Audio item not found", 404

    playlist, current_track_index = [], -1
    album_name = current_item.get('album')
    if album_name:
        query = f"SELECT id, title FROM `{table_name}` WHERE album = %s ORDER BY track_number, title ASC"
        playlist = db.get_data(query, (album_name,))
        if playlist:
            for i, track in enumerate(playlist):
                if track['id'] == item_id:
                    current_track_index = i
                    break

    return render_template('player.html', item=current_item, category=table_name, playlist=playlist, current_track_index=current_track_index)

@app.route('/update_resume/<string:table_name>/<int:item_id>', methods=['POST'])
def update_resume(table_name, item_id):
    position = request.form.get('position', 0)
    duration = request.form.get('duration', 0)
    position_to_save = float(position)
    if (float(duration) - position_to_save) < 15:
        position_to_save = 0
    query = f"UPDATE `{table_name}` SET resume_position = %s, last_played = NOW() WHERE id = %s"
    db.put_data(query, (position_to_save, item_id))
    return jsonify(status='success')

@app.route('/clear_resume/<string:table_name>/<int:item_id>', methods=['POST'])
def clear_resume(table_name, item_id):
    query = f"UPDATE `{table_name}` SET resume_position = 0 WHERE id = %s"
    db.put_data(query, (item_id,))
    return jsonify(status='success')

@app.route('/stream/<string:table_name>/<int:item_id>')
def stream(table_name, item_id):
    item = _get_item_details(table_name, item_id)
    if item and item.get('file_path'):
        return send_file(item['file_path'], as_attachment=False)
    return "File path not found", 404

@app.route('/get_pdf/<path:pdf_path>')
def get_pdf(pdf_path):
    full_path = os.path.join("/", pdf_path)
    safe_base_dir = os.path.abspath("/home/al/Media/Audio/")
    if not os.path.abspath(full_path).startswith(safe_base_dir):
        return "Access denied", 403
    return send_file(full_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5053, debug=True)
