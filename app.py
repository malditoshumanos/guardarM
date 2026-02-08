import argparse
import logging
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
    parser.add_argument("--db-host", required=False, default="localhost")
    parser.add_argument("--db-user", required=False, default="root")
    parser.add_argument("--db-password", required=False, default="rootpwd")
    parser.add_argument("--db-name", required=False, default="mividaprueba")
    parser.add_argument(
        "--download-dir", default="C:\\Users\\ASUS\\Music\\144_mividaprueba", help="Directory to store audio files"
    )
    return parser.parse_args()


def main() -> int:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    args = parse_args()
    logger.info(f"Starting playlist download: {args.playlist_url}")

    # Get playlist ID from URL
    try:
        logger.info("Extracting playlist ID...")
        playlist_id = extract_playlist_id(args.playlist_url)
        logger.info(f"Playlist ID extracted: {playlist_id}")
    except InvalidPlaylistURLError as exc:
        logger.error(f"Invalid playlist URL: {exc}")
        return 1


    # Connect to the database
    try:
        logger.info(f"Connecting to database: {args.db_host} / {args.db_name}")
        connection = get_connection(
            host=args.db_host,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
        )
        logger.info("Database connection established")
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1


    # Check if database exists 
    try:
        logger.info("Ensuring database schema...")
        ensure_schema(connection)
        logger.info("Upserting playlist to database...")
        upsert_playlist(connection, playlist_id, args.playlist_url)
        # Get already existing videos from the database 
        logger.info("Retrieving existing videos from database...")
        existing_video_ids = get_existing_video_ids(connection, playlist_id)
        logger.info(f"Found {len(existing_video_ids)} existing videos in database")
    except Exception as exc:
        logger.error(f"Database error: {exc}")
        return 1


    # gets the songs in the playlist 
    try:
        logger.info("Fetching playlist entries...")
        playlist_data = fetch_playlist_entries(args.playlist_url)
    except YtDlpError as exc:
        logger.error(f"yt-dlp error: {exc}")
        return 1
    # this returns a list of dics
    entries = playlist_data.get("entries", [])
    normalized_entries = normalize_entries(entries)
    logger.info(f"Total entries found in playlist: {len(normalized_entries)}")
    
    # Get playlist title and create playlist-specific directory
    playlist_title = playlist_data.get("title") or playlist_id
    logger.info(f"Playlist title: {playlist_title}")
    base_download_dir = Path(args.download_dir)
    logger.info(f"Creating base directory: {base_download_dir}")
    base_download_dir.mkdir(parents=True, exist_ok=True)
    download_dir = base_download_dir / playlist_title
    logger.info(f"Download directory: {download_dir}")

    # download and log into db 
    logger.info("Starting download process...")
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    for entry in normalized_entries:
        video_id = entry["video_id"]
        title = entry["title"]
        uploader = entry["uploader"]
        
        if video_id in existing_video_ids:
            logger.info(f"Skipping {title} (already downloaded)")
            skipped_count += 1
            continue
        
        video_url = entry["video_url"]
        logger.info(f"Downloading: {title} ({video_id})")
        
        try:
            file_path = download_audio(video_url, download_dir, video_title=title, uploader=uploader)
            logger.info(f"Successfully downloaded to: {file_path}")
        except YtDlpError as exc:
            logger.error(f"Failed to download {video_id}: {exc}")
            failed_count += 1
            continue

        try:
            # Use the actual filename (without extension) as the title in the database
            actual_filename = Path(file_path).stem
            logger.info(f"Inserting {video_id} into database...")
            insert_video(
                connection,
                playlist_id=playlist_id,
                video_id=video_id,
                title=actual_filename,
                video_url=video_url,
                downloaded_at=datetime.utcnow(),
                file_path=file_path,
            )
            downloaded_count += 1
            logger.info(f"Successfully recorded {video_id} in database")
        except Exception as exc:
            logger.error(f"Failed to record {video_id} in database: {exc}")
            failed_count += 1

    logger.info(f"Download process completed")
    logger.info(f"Summary - Downloaded: {downloaded_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    
    connection.close()
    logger.info("Connection closed. Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
