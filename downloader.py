import json
import subprocess
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


class YtDlpError(RuntimeError):
    pass


class InvalidPlaylistURLError(ValueError):
    pass


def extract_playlist_id(playlist_url: str) -> str:
    parsed = urlparse(playlist_url)
    query_params = parse_qs(parsed.query)
    playlist_ids = query_params.get("list")
    if not playlist_ids or not playlist_ids[0]:
        raise InvalidPlaylistURLError(
            "Playlist URL must include a 'list' query parameter."
        )
    return playlist_ids[0]


def fetch_playlist_entries(playlist_url: str) -> dict:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "-J", # fetch the playlist in json format
        playlist_url,
    ]
    # result contains result.returncode, result.stdout, result.stderr
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise YtDlpError(result.stderr.strip() or "yt-dlp failed to read playlist")
    data = json.loads(result.stdout)
    return data


def download_audio(video_url: str, output_dir: Path, video_title: str = None, uploader: str = None) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use video ID as temporary filename to ensure uniqueness during download
    output_template = str(output_dir / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-f", "bestaudio",
        "--no-playlist",
        "-o",
        output_template,
        "--print",
        "after_move:filepath",
        video_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise YtDlpError(result.stderr.strip() or "yt-dlp failed to download audio")
    file_path = result.stdout.strip().splitlines()[-1]
    if not file_path:
        raise YtDlpError("yt-dlp did not return a file path")
    
    # Rename file based on title and uploader
    if video_title:
        original_path = Path(file_path)
        ext = original_path.suffix
        
        # If title contains "-", use title as filename. Otherwise, use "CHANNEL - TITLE"
        if "-" in video_title:
            new_filename = f"{video_title}{ext}"
        else:
            if uploader:
                new_filename = f"{uploader} - {video_title}{ext}"
            else:
                new_filename = f"{video_title}{ext}"
        
        new_path = output_dir / new_filename
        # Avoid overwriting if file exists
        if new_path != original_path:
            original_path.rename(new_path)
        return str(new_path)
    
    return file_path


def normalize_entries(entries: Iterable[dict]) -> list[dict]:
    normalized = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        title = entry.get("title") or "(untitled)"
        uploader = entry.get("uploader") or entry.get("channel") or "Unknown"
        if not video_id:
            continue
        normalized.append(
            {
                "video_id": video_id,
                "title": title,
                "uploader": uploader,
                "video_url": YOUTUBE_WATCH_URL.format(video_id=video_id),
            }
        )
    return normalized
