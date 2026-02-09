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


def detect_platform(playlist_url: str) -> str:
    """
    Detect whether the URL is from YouTube or SoundCloud.
    Returns 'youtube' or 'soundcloud'
    """
    parsed = urlparse(playlist_url)
    domain = parsed.netloc.lower()
    
    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif "soundcloud.com" in domain:
        return "soundcloud"
    else:
        raise InvalidPlaylistURLError(
            f"Unsupported platform. URL must be from YouTube or SoundCloud."
        )


def extract_playlist_id(playlist_url: str) -> str:
    """
    Extract playlist ID from either YouTube or SoundCloud URL.
    For SoundCloud, returns the playlist URL itself since that's the identifier.
    """
    platform = detect_platform(playlist_url)
    
    if platform == "youtube":
        parsed = urlparse(playlist_url)
        query_params = parse_qs(parsed.query)
        playlist_ids = query_params.get("list")
        if not playlist_ids or not playlist_ids[0]:
            raise InvalidPlaylistURLError(
                "YouTube playlist URL must include a 'list' query parameter."
            )
        return playlist_ids[0]
    else:  # soundcloud
        # For SoundCloud, use the URL as the identifier
        return playlist_url


def fetch_playlist_entries(playlist_url: str, platform: str = "youtube") -> dict:
    """
    Fetch playlist entries. For SoundCloud, we don't use --flat-playlist
    because it returns url_transparent entries without track details.
    For YouTube, --flat-playlist is more efficient.
    """
    if platform == "soundcloud":
        # For SoundCloud: fetch full playlist info to get track details
        cmd = [
            "yt-dlp",
            "-J",  # fetch the playlist in json format
            playlist_url,
        ]
    else:
        # For YouTube: use flat-playlist for efficiency
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # fetch the playlist in json format
            playlist_url,
        ]
    
    # result contains result.returncode, result.stdout, result.stderr
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise YtDlpError(result.stderr.strip() or "yt-dlp failed to read playlist")
    data = json.loads(result.stdout)
    return data


def download_audio(video_url: str, output_dir: Path, video_title: str = None, uploader: str = None, video_id: str = None, platform: str = "youtube") -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use video ID as temporary filename to ensure uniqueness during download
    output_template = str(output_dir / "%(id)s.%(ext)s")
    
    # Platform-specific yt-dlp commands
    if platform == "soundcloud":
        # SoundCloud: no format filter needed (only one stream available)
        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o",
            output_template,
            "--print",
            "after_move:filepath",
            video_url,
        ]
    else:
        # YouTube: use format selection for best audio quality
        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-f", "bestaudio",
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
        
        # Handle filename collision: if file exists, append video_id to make it unique
        if new_path.exists():
            name_without_ext = new_path.stem
            new_filename = f"{name_without_ext}_{video_id}{ext}"
            new_path = output_dir / new_filename
        
        # Avoid renaming if source and target are the same
        if new_path != original_path:
            original_path.rename(new_path)
        return str(new_path)
    
    return file_path


def normalize_entries(entries: Iterable[dict], platform: str = "youtube") -> list[dict]:
    """
    Normalize entries from both YouTube and SoundCloud playlists.
    Handles different metadata structures from each platform.
    """
    normalized = []
    for entry in entries:
        if not entry:
            continue
        
        # Get the video ID
        video_id = entry.get("id")
        
        if not video_id:
            continue
        
        # Extract title - SoundCloud might use different field names
        if platform == "soundcloud":
            title = entry.get("title") or entry.get("track") or entry.get("display_name") or "(untitled)"
        else:
            title = entry.get("title") or "(untitled)"
        
        # Extract uploader - SoundCloud uses different field names
        if platform == "soundcloud":
            uploader = entry.get("uploader") or entry.get("creator") or entry.get("artist") or entry.get("channel") or "Unknown"
        else:
            uploader = entry.get("uploader") or entry.get("channel") or "Unknown"
        
        # Construct the appropriate URL based on platform
        if platform == "youtube":
            video_url = YOUTUBE_WATCH_URL.format(video_id=video_id)
        else:  # soundcloud
            # For SoundCloud, try to use the URL from the entry, or construct it
            video_url = entry.get("url") or entry.get("webpage_url") or f"https://soundcloud.com/unknown/{video_id}"
        
        normalized.append(
            {
                "video_id": str(video_id),
                "title": title,
                "uploader": uploader,
                "video_url": video_url,
            }
        )
    return normalized
