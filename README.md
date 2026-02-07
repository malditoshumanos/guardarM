# YouTube Playlist Audio Downloader

This project downloads audio from a YouTube playlist using `yt-dlp` and stores metadata in MySQL.

## SQL Schema

Use the schema below to create tables:

```sql
CREATE TABLE IF NOT EXISTS playlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id VARCHAR(255) NOT NULL UNIQUE,
    playlist_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id VARCHAR(255) NOT NULL,
    video_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    downloaded_at TIMESTAMP NOT NULL,
    file_path TEXT NOT NULL,
    UNIQUE KEY uniq_playlist_video (playlist_id, video_id)
);
```

You can also run `schema.sql` directly.

## Example Usage

```bash
python app.py \
  --playlist-url "https://www.youtube.com/playlist?list=PL123" \ 
  --db-host "localhost" \
  --db-user "root" \
  --db-password "password" \
  --db-name "youtube_audio" \
  --download-dir "downloads"
  ps. The only required argument is the playlist  
```

## Control Flow (Brief)

1. Parse CLI arguments and extract the playlist ID from the URL.
2. Connect to MySQL, ensure tables exist, and load existing video IDs for the playlist.
3. Use `yt-dlp` to retrieve playlist entries.
4. For each new video, download best-available audio and insert metadata into MySQL.
5. Skip videos already recorded for the playlist.
