# hygrep (hhg)

**Semantic code search with automatic indexing**

```bash
pip install hygrep
hhg "authentication flow" ./src
```

## What it does

Search your codebase using natural language. Results are functions and classes ranked by relevance:

```
$ hhg "error handling" ./tests/golden
No index found. Building...
Found 4 files (0.0s)
✓ Indexed 59 blocks from 4 files (5.4s)

Searching for: error handling
api_handlers.ts:127 function errorHandler
  function errorHandler(err: Error, req: Request, res: Response, next: NextFunc...
    console.error('API Error:', err.message);

errors.rs:7 class AppError
  pub enum AppError {
      /// Database operation failed.
      Database(DatabaseError),

2 results (0.60s)
```

## Search Modes

| Mode         | Flag      | Use Case                              |
| ------------ | --------- | ------------------------------------- |
| **Semantic** | (default) | Best quality, uses embeddings + index |
| **Fast**     | `-f`      | No index, grep + neural rerank        |
| **Exact**    | `-e`      | Fastest, literal string match         |
| **Regex**    | `-r`      | Pattern matching                      |

```bash
hhg "auth flow" ./src           # Semantic (auto-indexes on first run)
hhg -f "validate" ./src         # Grep + neural rerank (no index needed)
hhg -e "TODO" ./src             # Exact match (fastest)
hhg -r "TODO.*fix" ./src        # Regex match
```

## Install

Requires Python 3.11-3.13 (onnxruntime lacks 3.14 support).

```bash
pip install hygrep
# or
uv tool install hygrep --python 3.13
# or
pipx install hygrep
```

First search builds an index automatically (stored in `.hhg/`). Models are downloaded from HuggingFace and cached.

## Usage

```bash
hhg "query" [path]              # Search (default: current dir)
hhg -n 5 "error handling" .     # Limit results
hhg --json "auth" .             # JSON output for scripts/agents
hhg -l "config" .               # List matching files only
hhg -t py,js "api" .            # Filter by file type
hhg --exclude "tests/*" "fn" .  # Exclude patterns
hhg status [path]               # Check index status
hhg rebuild [path]              # Rebuild index from scratch
hhg clean [path]                # Delete index
```

**Note:** Options must come before positional arguments.

## Output

Default:

```
src/auth.py:42 function login
  def login(user, password):
      """Authenticate user and create session."""
      ...
```

JSON (`--json`):

```json
[
  {
    "file": "src/auth.py",
    "type": "function",
    "name": "login",
    "line": 42,
    "end_line": 58,
    "content": "def login(user, password): ...",
    "score": 0.87
  }
]
```

Compact JSON (`--json --compact`): Same fields without `content`.

## How it Works

**Semantic mode (default):**

```
Query → Embed → Vector search → Results
         ↓
    Auto-indexes on first run (.hhg/)
    Auto-updates when files change
```

**Fast mode (`-f`):**

```
Query → Grep scan → Tree-sitter extract → Neural rerank → Results
```

**Exact/Regex mode (`-e`/`-r`):**

```
Pattern → Grep scan → Tree-sitter extract → Results
```

## Supported Languages

Bash, C, C++, C#, Elixir, Go, Java, JavaScript, JSON, Kotlin, Lua, Mojo, PHP, Python, Ruby, Rust, Svelte, Swift, TOML, TypeScript, YAML, Zig

## Development

```bash
git clone https://github.com/nijaru/hygrep && cd hygrep
pixi install && pixi run build-ext && pixi run test
```

## License

MIT
