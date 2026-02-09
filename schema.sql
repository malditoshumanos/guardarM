CREATE TABLE IF NOT EXISTS playlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id VARCHAR(255) NOT NULL UNIQUE,
    playlist_url TEXT NOT NULL,
    playlist_title VARCHAR(255),
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
