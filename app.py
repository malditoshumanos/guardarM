import argparse
from datetime import datetime
from pathlib import Path

from db import (
    ensure_schema,
    get_connection,
    get_existing_video_ids,
    insert_video,
    upsert_playlist,
)
from downloader import (
    InvalidPlaylistURLError,
    YtDlpError,
    download_audio,
    extract_playlist_id,
    fetch_playlist_entries,
    normalize_entries,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download playlist audio with yt-dlp")
    parser.add_argument("--playlist-url", required=True, help="YouTube playlist URL")
    parser.add_argument("--db-host", required=True)
    parser.add_argument("--db-user", required=True)
    parser.add_argument("--db-password", required=True)
    parser.add_argument("--db-name", required=True)
    parser.add_argument(
        "--download-dir", default="downloads", help="Directory to store audio files"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        playlist_id = extract_playlist_id(args.playlist_url)
    except InvalidPlaylistURLError as exc:
        print(f"Invalid playlist URL: {exc}")
        return 1

    try:
        connection = get_connection(
            host=args.db_host,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    try:
        ensure_schema(connection)
        upsert_playlist(connection, playlist_id, args.playlist_url)
        existing_video_ids = get_existing_video_ids(connection, playlist_id)
    except Exception as exc:
        print(f"Database error: {exc}")
        return 1

    try:
        entries = fetch_playlist_entries(args.playlist_url)
    except YtDlpError as exc:
        print(f"yt-dlp error: {exc}")
        return 1

    normalized_entries = normalize_entries(entries)
    download_dir = Path(args.download_dir)

    for entry in normalized_entries:
        video_id = entry["video_id"]
        if video_id in existing_video_ids:
            continue
        video_url = entry["video_url"]
        title = entry["title"]
        try:
            file_path = download_audio(video_url, download_dir)
        except YtDlpError as exc:
            print(f"Failed to download {video_id}: {exc}")
            continue

        try:
            insert_video(
                connection,
                playlist_id=playlist_id,
                video_id=video_id,
                title=title,
                video_url=video_url,
                downloaded_at=datetime.utcnow(),
                file_path=file_path,
            )
        except Exception as exc:
            print(f"Failed to record {video_id} in database: {exc}")

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
