# hhg v2: Semantic Code Search

## Vision

**hhg is semantic code search.** You describe what you're looking for in natural language, it finds the relevant code.

If you want grep, use `rg`. If you want semantic understanding, use `hhg`.

## Core Principle

The index IS the product. Without embeddings, there's no semantic search. Accept this and design around it.

## UX

### First Use

```
$ hhg "authentication flow"
No index found. Building...
Scanning 847 files...
Embedding 3,241 code blocks...
✓ Ready (42s)

src/auth/login.py:23     authenticate_user()     0.94
src/auth/session.py:45   SessionManager          0.89
src/middleware/auth.py   verify_token()          0.85
```

**Auto-index on first query.** No separate build step. Just works.

### Subsequent Use

```
$ hhg "error handling"
src/utils/errors.py:12   handle_exception()      0.91
src/api/middleware.py:34 error_middleware()      0.88
...
```

Instant (<500ms). Index already exists.

### Index Maintenance

```
$ hhg "query"
⚠ 47 files changed since last index
Updating... ✓ (3s)

src/...
```

**Auto-update when stale.** Incremental, fast, transparent.

### Exact Match Escape Hatch

```
$ hhg -e "TODO"           # Exact string match (grep)
$ hhg -r "TODO.*fix"      # Regex match
```

For when you know exactly what you're looking for.

## Commands

```
hhg <query> [path]        # Semantic search (builds/updates index as needed)
hhg -e <pattern> [path]   # Exact match (no index, instant)
hhg -r <pattern> [path]   # Regex match (no index, instant)
hhg status [path]         # Show index stats
hhg rebuild [path]        # Force full rebuild
hhg clean [path]          # Delete index
```

That's it. No `index build`, no `--semantic`, no `--hybrid`. One tool, one job.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        hhg "query"                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Index exists?  │
                    └─────────────────┘
                         │         │
                        No        Yes
                         │         │
                         ▼         ▼
                   ┌──────────┐  ┌──────────┐
                   │  Build   │  │  Fresh?  │
                   │  Index   │  └──────────┘
                   └──────────┘    │      │
                         │        No     Yes
                         │         │      │
                         │         ▼      │
                         │   ┌──────────┐ │
                         │   │  Update  │ │
                         │   └──────────┘ │
                         │         │      │
                         └────┬────┴──────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Embed Query     │
                    │ Vector Search   │
                    │ Return Results  │
                    └─────────────────┘
```

## Index Design

### Storage

```
.hhg/
├── meta.json           # Version, timestamps, file hashes
├── vectors.db          # omendb: embeddings + metadata
└── .gitignore          # Auto-created: "*"
```

### What Gets Indexed

Tree-sitter extracts semantic units:

- Functions/methods
- Classes/structs/traits
- Type definitions
- Top-level constants

Each block stores:

- File path
- Line range (start, end)
- Symbol name
- Symbol type (function, class, etc.)
- Full content
- Embedding vector (384 dims)

### Incremental Updates

```python
def update_index(root: Path) -> None:
    meta = load_meta()

    for file in scan_files(root):
        file_hash = hash_file(file)

        if meta.hashes.get(file) == file_hash:
            continue  # Unchanged

        if file in meta.hashes:
            db.delete_by_file(file)  # Remove old blocks

        blocks = extract_blocks(file)
        embeddings = embed(blocks)
        db.insert(blocks, embeddings)

        meta.hashes[file] = file_hash

    # Remove deleted files
    for file in meta.hashes:
        if not file.exists():
            db.delete_by_file(file)
            del meta.hashes[file]

    save_meta(meta)
```

## Output Format

### Default (TTY)

```
$ hhg "database connection pooling"
src/db/pool.py:34        ConnectionPool          0.94
  class ConnectionPool:
      """Manages database connection pooling."""

src/db/connection.py:12  get_connection()        0.89
  def get_connection(timeout: int = 30) -> Connection:
      """Get a connection from the pool."""
```

Context snippet shown. Color-coded by type.

### Compact

```
$ hhg "database connection" -c
src/db/pool.py:34        ConnectionPool          0.94
src/db/connection.py:12  get_connection()        0.89
src/db/config.py:5       DatabaseConfig          0.85
```

### JSON

```
$ hhg "database" --json
[
  {
    "file": "src/db/pool.py",
    "line": 34,
    "end_line": 78,
    "name": "ConnectionPool",
    "type": "class",
    "score": 0.94,
    "content": "class ConnectionPool:..."
  }
]
```

## Flags

| Flag          | Short | Description                         |
| ------------- | ----- | ----------------------------------- |
| `--exact`     | `-e`  | Exact string match (grep mode)      |
| `--regex`     | `-r`  | Regex match                         |
| `--json`      | `-j`  | JSON output                         |
| `--compact`   | `-c`  | No content preview                  |
| `--num`       | `-n`  | Number of results (default: 10)     |
| `--type`      | `-t`  | Filter by type (function, class)    |
| `--file`      | `-f`  | Filter by file pattern              |
| `--threshold` |       | Min similarity score (default: 0.5) |
| `--no-update` |       | Don't auto-update stale index       |
| `--quiet`     | `-q`  | Suppress progress output            |

## Performance

| Operation          | Target         | How               |
| ------------------ | -------------- | ----------------- |
| First index        | <60s/10k files | Batch embedding   |
| Incremental update | <100ms/file    | Delta only        |
| Search             | <200ms         | Vector similarity |
| Exact match        | <50ms          | No index, grep    |

## Configuration

```toml
# .hhg/config.toml or pyproject.toml [tool.hhg]
[hhg]
num = 10
threshold = 0.5
auto_update = true       # Update stale index automatically
stale_after = 50         # Files changed before considered stale

[hhg.exclude]
patterns = ["*_test.py", "vendor/*"]
```

## Migration from v1

v1 users get a one-time message:

```
hhg v2 is semantic-first. Your query will build an index.
For grep-style search, use: hhg -e "pattern"
For regex search, use: hhg -r "pattern"

Continue? [Y/n]
```

After first use, no more prompts.

## Why This Design

1. **One mental model**: hhg = semantic search. Period.

2. **Zero friction**: First query just works. No setup commands.

3. **Always fresh**: Auto-update means results are current.

4. **Escape hatches exist**: `-e` and `-r` for exact/regex when needed.

5. **No mode confusion**: No `--fast`, `--semantic`, `--hybrid`. One mode.

6. **Index is invisible**: Users don't think about it. It's an implementation detail.

## What We're Dropping

- `--fast` mode (use `rg` instead)
- Cross-encoder reranking (embeddings are good enough)
- Explicit `index build` command (auto on first use)
- `--hybrid` mode (semantic is the default)
- Multiple search modes (one tool, one job)

## Implementation

### Phase 1: Core

- [ ] Auto-index on first query
- [ ] Auto-update when stale
- [ ] Clean output format
- [ ] `-e` and `-r` escape hatches

### Phase 2: Polish

- [ ] Progress indicators
- [ ] Config file support
- [ ] File/type filters
- [ ] Threshold tuning

### Phase 3: Performance

- [ ] Parallel embedding
- [ ] Index compression
- [ ] Lazy loading
