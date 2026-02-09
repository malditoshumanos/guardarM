import mysql.connector
from mysql.connector import Error


def get_connection(host: str, user: str, password: str, database: str):
    try:
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
        )
    except Error as exc:
        raise RuntimeError(f"Database connection failed: {exc}") from exc

# create tables if they don't exist
def ensure_schema(connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playlists (
            id INT AUTO_INCREMENT PRIMARY KEY,
            playlist_id VARCHAR(255) NOT NULL UNIQUE,
            playlist_url TEXT NOT NULL,
            playlist_title VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            playlist_id VARCHAR(255) NOT NULL,
            video_id VARCHAR(255) NOT NULL,
            title TEXT NOT NULL,
            video_url TEXT NOT NULL,
            downloaded_at TIMESTAMP NOT NULL,
            file_path TEXT NOT NULL,
            UNIQUE KEY uniq_playlist_video (playlist_id, video_id)
        )
        """
    )
    connection.commit()
    cursor.close()

# get songs already in the database for a given playlist
def get_existing_video_ids(connection, playlist_id: str) -> set[str]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT video_id FROM videos WHERE playlist_id = %s",
        (playlist_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return {row[0] for row in rows}

# upsert means update or insert 
def upsert_playlist(connection, playlist_id: str, playlist_url: str, playlist_title: str = None) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO playlists (playlist_id, playlist_url, playlist_title)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE playlist_url = VALUES(playlist_url), playlist_title = VALUES(playlist_title)
        """,
        (playlist_id, playlist_url, playlist_title),
    )
    connection.commit()
    cursor.close()


def insert_video(
    connection,
    playlist_id: str,
    video_id: str,
    title: str,
    video_url: str,
    downloaded_at,
    file_path: str,
) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO videos (
            playlist_id, video_id, title, video_url, downloaded_at, file_path
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (playlist_id, video_id, title, video_url, downloaded_at, file_path),
    )
    connection.commit()
    cursor.close()
