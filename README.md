# hygrep (hhg)

**Grep + neural reranking for code search**

```bash
pip install hygrep
hhg "auth" ./src
```

## What it does

1. **Grep**: Regex search finds files containing your query
2. **Extract**: Tree-sitter parses matching files to pull out functions/classes
3. **Rerank**: Neural model scores each code block by relevance to your query

**Not semantic search** - no embeddings, no vector DB. Just grep → parse → rerank.

- **Smart context:** Returns full functions/classes, not just lines
- **Fast:** Parallel regex recall, then neural reranking
- **Zero indexing:** Works instantly on any codebase

## Install

```bash
pip install hygrep
# or
uv tool install hygrep
# or
pipx install hygrep
```

The binary name for hygrep is `hhg`.

First search downloads the model (~83MB, cached in `~/.cache/huggingface/`).

## Usage

```bash
hhg "query" [path]           # Search (default: current dir)
hhg "error handling" . -n 5  # Limit to 5 results
hhg "auth" . --fast          # Skip reranking (instant grep)
hhg "test" . -t py,js        # Filter by file type
hhg "config" . --json        # JSON output for agents/scripts
hhg info                     # Check installation status
hhg model                    # Show model info
hhg model install            # Pre-download model (for CI/offline)
hhg model clean              # Remove cached model
```

Run `hhg --help` for all options.

## Output

```
src/auth.py:42 [function] login (0.89)
src/session.py:15 [function] validate_token (0.76)
```

With `--json`:

```json
[
  {
    "file": "src/auth.py",
    "type": "function",
    "name": "login",
    "start_line": 42,
    "score": 0.89,
    "content": "def login(user): ..."
  }
]
```

## Config

Optional `~/.config/hygrep/config.toml`:

```toml
n = 10
color = "always"
exclude = ["*.test.js", "tests/*"]
cache_dir = "~/.cache/hygrep"  # Custom model cache (default: shared HF cache)
```

## Supported Languages

Bash, C, C++, C#, Elixir, Go, Java, JavaScript, JSON, Kotlin, Lua, Mojo, PHP, Python, Ruby, Rust, Svelte, Swift, TOML, TypeScript, YAML, Zig

## How it works

```
Query → Parallel regex scan → Tree-sitter extraction → ONNX reranking → Results
```

| Stage   | What                                          |
| ------- | --------------------------------------------- |
| Recall  | Mojo/Python parallel scanner (~20k files/sec) |
| Extract | Tree-sitter AST (functions, classes)          |
| Rerank  | ONNX cross-encoder (mxbai-rerank-xsmall-v1)   |

## Development

```bash
git clone https://github.com/nijaru/hygrep && cd hygrep
pixi install && pixi run build-ext && pixi run test
```

## License

MIT
