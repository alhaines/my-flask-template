#!/home/$USER/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
#   filename:  /home/$USER/projects/audio-player/read_audio_to_mysql.py
#
#   Copyright 2025 AL Haines

import os
import pymysql
import re
from config_audio import mysql_config

# fix for the location of your files
table_list = [
    ("/home/$USER/Media/Audio/Audiobooks", "audio_audiobooks"),
    ("/home/$USER/Media/Audio/Comedy", "audio_comedy"),
    ("/home/$USER/Media/Audio/Instructional", "audio_instructional"),
    ("/home/$USER/Media/Audio/Collections", "audio_collections"),
    ("/home/$USER/Media/Audio/Singles", "audio_singles")
]
audio_pattern = re.compile(r'.*(\.mp3|\.wav|\.flac|\.ogg|\.m4a)$', re.IGNORECASE)

def connect_to_db():
    return pymysql.connect(**mysql_config)

def insert_new_files(connection, folder_path, table_name, pattern):
    cursor = connection.cursor()
    # TRUNCATE the table to ensure a fresh import
    cursor.execute(f"TRUNCATE TABLE `{table_name}`")
    print(f"Scanning and importing to: {table_name}")

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if pattern.match(file):
                file_path = os.path.join(root, file)
                title = os.path.splitext(file)[0]
                album = os.path.basename(root)
                track_number = None

                # --- NEW: Try to extract track number from filename ---
                match = re.match(r'^\s*(\d+)', title)
                if match:
                    track_number = int(match.group(1))

                try:
                    cursor.execute(
                        f"INSERT INTO `{table_name}` (title, file_path, album, track_number) VALUES (%s, %s, %s, %s)",
                        (title, file_path, album, track_number),
                    )
                except pymysql.Error as e:
                    print(f"Error inserting {file_path}: {e}")
    connection.commit()
    print(f"Finished importing to {table_name}.")

if __name__ == "__main__":
    db_connection = connect_to_db()
    if db_connection:
        for folder_path, table_name in table_list:
            if os.path.exists(folder_path):
                insert_new_files(db_connection, folder_path, table_name, audio_pattern)
            else:
                print(f"Warning: Folder not found - {folder_path}")
        db_connection.close()
