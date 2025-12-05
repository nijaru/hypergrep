"""Semantic search using embeddings + omendb vector database."""

import hashlib
import json
from pathlib import Path

from .embedder import DIMENSIONS, Embedder
from .extractor import ContextExtractor

# Try to import omendb
try:
    import omendb

    HAS_OMENDB = True
except ImportError:
    HAS_OMENDB = False


INDEX_DIR = ".hhg"
VECTORS_DIR = "vectors"
MANIFEST_FILE = "manifest.json"


class SemanticIndex:
    """Manages semantic search index using omendb."""

    def __init__(self, root: Path, cache_dir: str | None = None):
        if not HAS_OMENDB:
            raise ImportError(
                "omendb is required for semantic search. Install with: pip install omendb"
            )

        self.root = Path(root).resolve()
        self.index_dir = self.root / INDEX_DIR
        self.vectors_path = str(self.index_dir / VECTORS_DIR)
        self.manifest_path = self.index_dir / MANIFEST_FILE

        self.embedder = Embedder(cache_dir=cache_dir)
        self.extractor = ContextExtractor()

        self._db: "omendb.Database | None" = None

    def _ensure_db(self) -> "omendb.Database":
        """Open or create the vector database."""
        if self._db is None:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            self._db = omendb.open(self.vectors_path, dimensions=DIMENSIONS)
        return self._db

    def _file_hash(self, path: Path) -> str:
        """Get hash of file content for change detection."""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    def _load_manifest(self) -> dict:
        """Load manifest of indexed files.

        Manifest format v2:
            {"files": {"path": {"hash": "abc123", "blocks": ["id1", "id2"]}}}

        Migrates from v1 format ({"files": {"path": "hash"}}) on load.
        """
        if self.manifest_path.exists():
            data = json.loads(self.manifest_path.read_text())
            # Migrate v1 -> v2 format
            files = data.get("files", {})
            for path, value in list(files.items()):
                if isinstance(value, str):
                    # v1 format: just hash string
                    files[path] = {"hash": value, "blocks": []}
            return data
        return {"files": {}}

    def _save_manifest(self, manifest: dict) -> None:
        """Save manifest."""
        self.manifest_path.write_text(json.dumps(manifest, indent=2))

    def index(
        self,
        files: dict[str, str],
        batch_size: int = 128,
        on_progress: callable = None,
    ) -> dict:
        """Index code files for semantic search.

        Args:
            files: Dict mapping file paths to content.
            batch_size: Number of code blocks to embed at once.
            on_progress: Callback(current, total, message) for progress updates.

        Returns:
            Stats dict with counts.
        """
        db = self._ensure_db()
        manifest = self._load_manifest()

        stats = {"files": 0, "blocks": 0, "skipped": 0, "errors": 0, "deleted": 0}

        # Collect all code blocks
        all_blocks = []
        files_to_update = {}  # Track which files we're updating

        for file_path, content in files.items():
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            # Skip unchanged files
            file_entry = manifest["files"].get(file_path, {})
            if isinstance(file_entry, dict) and file_entry.get("hash") == file_hash:
                stats["skipped"] += 1
                continue

            # Delete old vectors for this file before re-indexing
            old_blocks = file_entry.get("blocks", []) if isinstance(file_entry, dict) else []
            if old_blocks:
                db.delete(old_blocks)
                stats["deleted"] += len(old_blocks)

            # Extract code blocks
            try:
                blocks = self.extractor.extract(file_path, query="", content=content)
                new_block_ids = []
                for block in blocks:
                    block_id = f"{file_path}:{block['start_line']}:{block['name']}"
                    new_block_ids.append(block_id)
                    all_blocks.append(
                        {
                            "id": block_id,
                            "file": file_path,
                            "file_hash": file_hash,
                            "block": block,
                            "text": f"{block['type']} {block['name']}\n{block['content']}",
                        }
                    )
                files_to_update[file_path] = {"hash": file_hash, "blocks": new_block_ids}
                stats["files"] += 1
            except Exception:
                stats["errors"] += 1
                continue

        if not all_blocks:
            return stats

        # Batch embed and store
        total = len(all_blocks)
        for i in range(0, total, batch_size):
            batch = all_blocks[i : i + batch_size]
            texts = [b["text"] for b in batch]

            if on_progress:
                on_progress(i, total, f"Embedding {len(batch)} blocks...")

            # Generate embeddings
            embeddings = self.embedder.embed(texts)

            # Store in omendb
            items = []
            for j, block_info in enumerate(batch):
                items.append(
                    {
                        "id": block_info["id"],
                        "embedding": embeddings[j].tolist(),
                        "metadata": {
                            "file": block_info["file"],
                            "type": block_info["block"]["type"],
                            "name": block_info["block"]["name"],
                            "start_line": block_info["block"]["start_line"],
                            "end_line": block_info["block"]["end_line"],
                            "content": block_info["block"]["content"],
                        },
                    }
                )

            db.set(items)
            stats["blocks"] += len(batch)

        # Update manifest with new file entries
        for file_path, file_info in files_to_update.items():
            manifest["files"][file_path] = file_info

        if on_progress:
            on_progress(total, total, "Done")

        self._save_manifest(manifest)
        return stats

    def search(self, query: str, k: int = 10) -> list[dict]:
        """Search for code blocks similar to query.

        Args:
            query: Natural language query.
            k: Number of results to return.

        Returns:
            List of results with file, type, name, content, score.
        """
        db = self._ensure_db()

        # Embed query
        query_embedding = self.embedder.embed_one(query)

        # Search
        results = db.search(query_embedding.tolist(), k=k)

        # Format results
        output = []
        for r in results:
            meta = r.get("metadata", {})
            output.append(
                {
                    "file": meta.get("file", ""),
                    "type": meta.get("type", ""),
                    "name": meta.get("name", ""),
                    "line": meta.get("start_line", 0),
                    "end_line": meta.get("end_line", 0),
                    "content": meta.get("content", ""),
                    "score": (2.0 - r.get("distance", 0))
                    / 2.0,  # Cosine distance 0-2 → similarity 0-1
                }
            )

        return output

    def is_indexed(self) -> bool:
        """Check if index exists."""
        return self.manifest_path.exists()

    def count(self) -> int:
        """Count indexed vectors."""
        if not self.is_indexed():
            return 0
        db = self._ensure_db()
        return db.count()

    def get_stale_files(self, files: dict[str, str]) -> tuple[list[str], list[str]]:
        """Find files that need reindexing.

        Returns:
            Tuple of (changed_files, deleted_files)
        """
        manifest = self._load_manifest()
        indexed_files = manifest.get("files", {})

        changed = []
        for file_path, content in files.items():
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            file_entry = indexed_files.get(file_path, {})
            stored_hash = file_entry.get("hash") if isinstance(file_entry, dict) else file_entry
            if stored_hash != file_hash:
                changed.append(file_path)

        # Files in manifest but not in current scan = deleted
        current_files = set(files.keys())
        deleted = [f for f in indexed_files if f not in current_files]

        return changed, deleted

    def needs_update(self, files: dict[str, str]) -> int:
        """Quick check: how many files need updating?"""
        changed, deleted = self.get_stale_files(files)
        return len(changed) + len(deleted)

    def update(
        self,
        files: dict[str, str],
        on_progress: callable = None,
    ) -> dict:
        """Incremental update - only reindex changed files.

        Args:
            files: Dict mapping file paths to content (all files).
            on_progress: Callback for progress updates.

        Returns:
            Stats dict with counts.
        """
        changed, deleted = self.get_stale_files(files)

        if not changed and not deleted:
            return {"files": 0, "blocks": 0, "deleted": 0, "skipped": len(files)}

        db = self._ensure_db()
        manifest = self._load_manifest()

        # Delete vectors for deleted files
        deleted_count = 0
        if deleted:
            for f in deleted:
                file_entry = manifest["files"].get(f, {})
                old_blocks = file_entry.get("blocks", []) if isinstance(file_entry, dict) else []
                if old_blocks:
                    db.delete(old_blocks)
                    deleted_count += len(old_blocks)
                manifest["files"].pop(f, None)
            self._save_manifest(manifest)

        # Re-index changed files (index() handles deleting old vectors)
        changed_files = {f: files[f] for f in changed if f in files}
        stats = self.index(changed_files, on_progress=on_progress)
        stats["deleted"] = stats.get("deleted", 0) + deleted_count

        return stats

    def clear(self) -> None:
        """Delete the index."""
        import shutil

        if self.index_dir.exists():
            shutil.rmtree(self.index_dir)
