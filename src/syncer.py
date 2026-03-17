"""Sync Google Drive Gemini meeting notes to local Markdown files."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from src.document_parser import parse_gemini_document
from src.drive_client import DriveClient
from src.index_manager import IndexManager
from src.markdown_writer import generate_filename, write_meeting_markdown
from src.models import Meeting, MeetingIndexEntry

logger = logging.getLogger(__name__)


class Syncer:
    def __init__(self, meetings_dir: Path, drive_client: DriveClient) -> None:
        self._meetings_dir = meetings_dir
        self._drive = drive_client
        self._index_manager = IndexManager(meetings_dir)

    def sync(self) -> None:
        index = self._index_manager.load()
        logger.info("Sync started. Last sync: %s", index.last_sync)
        try:
            docs = self._drive.list_meeting_notes(since=index.last_sync)
        except Exception as e:
            logger.error("Failed to list meeting notes: %s", e)
            return
        logger.info("Found %d documents to process.", len(docs))
        for doc in docs:
            try:
                self._process_document(doc, index)
            except Exception as e:
                logger.error("Failed to process document %s: %s", doc.get("id"), e)
                continue
        index.last_sync = datetime.now(tz=timezone.utc)
        self._index_manager.save(index)
        logger.info("Sync completed. Processed %d documents.", len(docs))

    def _process_document(self, doc: dict, index) -> None:
        doc_id = doc["id"]
        doc_title = doc["name"]
        logger.info("Processing: %s (%s)", doc_title, doc_id)
        content = self._drive.download_document(doc_id)
        parsed = parse_gemini_document(content, doc_title=doc_title)
        meeting = Meeting(
            id=str(uuid.uuid4())[:8],
            title=parsed.title,
            date=parsed.date or datetime.now(tz=timezone.utc),
            duration_minutes=parsed.duration_minutes,
            participants=parsed.participants,
            source_doc_id=doc_id,
            synced_at=datetime.now(tz=timezone.utc),
            tags=[],
            summary=parsed.summary,
            transcript=parsed.transcript,
            action_items=parsed.action_items,
            parse_warnings=parsed.parse_warnings,
        )
        existing = index.find_by_source_doc_id(doc_id)
        if existing:
            meeting.id = existing.id
        path = write_meeting_markdown(meeting, self._meetings_dir)
        entry = MeetingIndexEntry.from_meeting(meeting, path.name)
        self._index_manager.add_or_update_entry(index, entry)


def _setup_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(exist_ok=True)
    handler = TimedRotatingFileHandler(
        logs_dir / "sync.log", when="midnight", backupCount=30, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    meetings_dir = project_root / "meetings"
    logs_dir = project_root / "logs"
    _setup_logging(logs_dir)
    meetings_dir.mkdir(exist_ok=True)
    settings_path = config_dir / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    folder_name = settings.get("drive_folder_name", "Meeting notes")
    try:
        drive = DriveClient(config_dir=config_dir, folder_name=folder_name)
    except Exception as e:
        logger.error("Failed to initialize Drive client: %s", e)
        return
    syncer = Syncer(meetings_dir=meetings_dir, drive_client=drive)
    syncer.sync()


if __name__ == "__main__":
    main()
