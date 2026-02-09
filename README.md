# Playlist Audio Downloader

Download audio from **YouTube** and **SoundCloud** playlists using `yt-dlp` and store metadata in MySQL.

## Features

- ✅ **Multi-platform support**: Download from YouTube and SoundCloud playlists
- ✅ **High-quality audio**: MP3 V0 codec (192-320 kbps variable bitrate)
- ✅ **Smart filename formatting**: 
  - If title contains "-": uses the video title as filename
  - Otherwise: uses `[CHANNEL NAME] - [VIDEO TITLE]` format
- ✅ **Collision handling**: Appends video ID if filename already exists
- ✅ **Organized directories**: Songs are saved in `[base-dir]/[Playlist Name]/`
- ✅ **Automatic folder creation**: Creates necessary directories if they don't exist
- ✅ **Comprehensive logging**: Detailed console output showing each step of the process
- ✅ **Database sync**: Tracks downloaded files and prevents duplicates
- ✅ **Metadata consistency**: Database title field matches the actual filename
- ✅ **Playlist tracking**: Stores playlist title in database for better organization

## Requirements

- Python 3.9+
- `yt-dlp` (for downloading)
- `ffmpeg` (for audio conversion)
- MySQL server

## SQL Schema

Use the schema below to create tables:

```sql
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
```

You can also run `schema.sql` directly.

## Usage

### Basic Example (YouTube)

```bash
python app.py --playlist-url "https://www.youtube.com/playlist?list=PL123"
```

### Full Example with all options

```bash
python app.py \
  --playlist-url "https://www.youtube.com/playlist?list=PL123" \
  --db-host "localhost" \
  --db-user "root" \
  --db-password "password" \
  --db-name "mivida" \
  --download-dir "C:\Users\ASUS\Music\144_mividaprueba"
```

### SoundCloud Example

```bash
python app.py --playlist-url "https://soundcloud.com/user/sets/playlist-name"
```

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--playlist-url` | Yes | - | YouTube or SoundCloud playlist URL |
| `--db-host` | No | `localhost` | MySQL server host |
| `--db-user` | No | `root` | MySQL username |
| `--db-password` | No | `rootpwd` | MySQL password |
| `--db-name` | No | `mivida` | Database name |
| `--download-dir` | No | `C:\Users\ASUS\Music\144_mividaprueba` | Base directory for downloads |

## Output Structure

```
C:\Users\ASUS\Music\144_mividaprueba\
├── Liked Playlist\
│   ├── Artist Name - Song Title.mp3
│   ├── Another Artist - Another Song.mp3
│   └── Song - With Dash.mp3
└── Another Playlist\
    └── Channel - Track.mp3
```

## Control Flow

1. **Detect platform** - Analyze URL to determine YouTube or SoundCloud
2. **Extract playlist ID** - Get playlist identifier from URL
3. **Connect to database** - Establish MySQL connection and ensure schema exists
4. **Fetch playlist data** - Retrieve metadata and entries:
   - **YouTube**: Uses `--flat-playlist` for efficiency
   - **SoundCloud**: Fetches full playlist to get track titles and artist info
5. **Store playlist info** - Save playlist title and metadata to database
6. **Check existing tracks** - Query database to prevent re-downloading
7. **Download tracks** - For each new track:
   - Use platform-specific yt-dlp command:
     - **YouTube**: `-f bestaudio` to select best quality
     - **SoundCloud**: No format filter (single stream available)
   - Extract audio and convert to MP3 V0
   - Rename file based on title and uploader
   - Handle filename collisions by appending video ID
8. **Update database** - Record download metadata
9. **Provide summary** - Log download/skip/failure counts

## Logging

The application provides detailed logging with timestamps:

```
[2026-02-08 14:30:45] INFO: Starting playlist download: https://...
[2026-02-08 14:30:45] INFO: Platform detected: youtube
[2026-02-08 14:30:46] INFO: Downloading: Song Title (video_id)
[2026-02-08 14:30:50] INFO: Successfully downloaded to: C:\path\to\file.mp3
[2026-02-08 14:31:22] INFO: Summary - Downloaded: 5, Skipped: 2, Failed: 0
```

## Database

The application tracks the following information:

**Playlists table:**
- Playlist URL and ID (unique)
- **Playlist title** - Name of the playlist from the platform
- Creation timestamp

**Videos table:**
- Playlist ID (foreign key)
- Video/track ID
- Title (matches filename without extension)
- Original URL to the track
- Download timestamp
- Local file path
