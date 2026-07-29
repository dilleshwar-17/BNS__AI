"""
Legal Data Ingestion Pipeline

Periodically checks for updates to Indian legal data from public sources
and updates the local knowledge base, vector store, and graph.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "kb"
UPDATE_LOG = DATA_DIR / "update_log.json"
OFFLINE_KB_PATH = DATA_DIR / "offline_knowledge_base.json"


class LegalDataIngestor:
    def __init__(self):
        self.sources = {
            "indian_kanoon": {
                "base_url": "https://api.indiankanoon.org",
                "check_interval_hours": 24,
            },
            "india_code": {
                "base_url": "https://www.indiacode.nic.in",
                "check_interval_hours": 168,  # weekly
            },
        }
        self._last_check: dict[str, float] = {}
        self._running = False

    def _load_update_log(self) -> dict:
        if UPDATE_LOG.exists():
            return json.loads(UPDATE_LOG.read_text())
        return {"last_updates": {}, "checksums": {}}

    def _save_update_log(self, log: dict):
        UPDATE_LOG.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_LOG.write_text(json.dumps(log, indent=2))

    def _compute_checksum(self, path: Path) -> str:
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    async def check_for_updates(self) -> dict[str, bool]:
        log = self._load_update_log()
        updates = {}

        # Check offline KB
        kb_checksum = self._compute_checksum(OFFLINE_KB_PATH)
        old_checksum = log.get("checksums", {}).get("offline_kb", "")
        if kb_checksum and kb_checksum != old_checksum:
            updates["offline_kb"] = True
            log.setdefault("checksums", {})["offline_kb"] = kb_checksum

        # Check for new data files in data/kb/
        for f in DATA_DIR.glob("*.json"):
            if f.name == "update_log.json":
                continue
            key = f.stem
            checksum = self._compute_checksum(f)
            old = log.get("checksums", {}).get(key, "")
            if checksum and checksum != old:
                updates[key] = True
                log.setdefault("checksums", {})
                log["checksums"][key] = checksum

        self._save_update_log(log)
        return updates

    async def ingest_update(self, source: str, data: dict) -> bool:
        try:
            if source == "offline_kb":
                return await self._update_offline_kb(data)
            elif source.endswith("_kb"):
                return await self._update_external_kb(source, data)
            return False
        except Exception as e:
            logger.error("ingest_update_failed", source=source, error=str(e))
            return False

    async def _update_offline_kb(self, data: dict) -> bool:
        from app.ingestion.chroma.vector_store import _get_client, _run_sync

        def _update():
            client = _get_client()
            try:
                collection = client.get_collection("bnsai_legal")
            except Exception:
                collection = client.create_collection("bnsai_legal")

            existing_ids = set()
            try:
                result = collection.get(include=[])
                existing_ids = set(result.get("ids", []))
            except Exception:
                pass

            new_count = 0
            for topic_id, entry in data.items():
                doc_id = f"legal_{topic_id}"
                text = (
                    f"{entry['title']}. {entry['description']} {entry.get('procedure', '')} {entry.get('citation', '')}"
                )
                if doc_id in existing_ids:
                    collection.update(
                        ids=[doc_id],
                        documents=[text],
                        metadatas=[{"topic": topic_id, "title": entry["title"]}],
                    )
                else:
                    collection.add(
                        documents=[text],
                        metadatas=[{"topic": topic_id, "title": entry["title"]}],
                        ids=[doc_id],
                    )
                    new_count += 1

            logger.info("offline_kb_updated", new=new_count, total=len(data))
            return True

        await _run_sync(_update)
        return True

    async def _update_external_kb(self, source: str, data: dict) -> bool:
        logger.info("external_kb_update", source=source, entries=len(data))
        return True

    async def run_update_cycle(self):
        log = self._load_update_log()
        now = time.time()

        updates = await self.check_for_updates()
        if not updates:
            logger.debug("no_updates_found")
            return {"updated": False}

        results = {}
        for source, has_update in updates.items():
            if not has_update:
                continue

            kb_path = DATA_DIR / f"{source}.json"
            if not kb_path.exists() and source != "offline_kb":
                continue

            if source == "offline_kb":
                data = json.loads(OFFLINE_KB_PATH.read_text()) if OFFLINE_KB_PATH.exists() else {}
            else:
                data = json.loads(kb_path.read_text())

            success = await self.ingest_update(source, data)
            results[source] = success

            if success:
                log.setdefault("last_updates", {})[source] = datetime.now(timezone.utc).isoformat()
                self._last_check[source] = now

        self._save_update_log(log)

        # Publish update events
        try:
            from app.core.events import publish_event

            for source, success in results.items():
                if success:
                    await publish_event(
                        "ingestion.completed",
                        {"source": source, "timestamp": datetime.now(timezone.utc).isoformat()},
                        source="legal_data_ingestor",
                    )
        except Exception:
            pass

        logger.info("update_cycle_complete", results=results)
        return {"updated": True, "results": results}

    async def start_periodic_updates(self, interval_seconds: int = 3600):
        self._running = True
        logger.info("periodic_update_started", interval=interval_seconds)
        while self._running:
            try:
                await self.run_update_cycle()
            except Exception as e:
                logger.error("periodic_update_error", error=str(e))
            await asyncio.sleep(interval_seconds)

    def stop(self):
        self._running = False


ingestor = LegalDataIngestor()


async def run_legal_data_update():
    return await ingestor.run_update_cycle()
