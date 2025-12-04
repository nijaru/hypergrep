# hygrep (hhg)

**Grep + neural reranking for code search. Not semantic search - uses regex matching, then reranks results by relevance.**

How it works:
1. **Grep stage**: Regex pattern matching across files (POSIX regex via libc)
2. **Extract stage**: Tree-sitter parses matched files to extract functions/classes
3. **Rerank stage**: Cross-encoder scores extracted code by query relevance

No embeddings, no vector DB, no indexing. Just grep → parse → rerank.

## Quick Reference

```bash
pixi run build-ext            # Build Mojo scanner extension
pixi run hhg "query" ./src    # Search
pixi run hhg "query" . --json # Agent output
pixi run test                 # Run all tests
```

## Architecture

```
Query → [Mojo Scanner] → matching files → [Tree-sitter] → code blocks → [ONNX Reranker] → ranked results
              ↓                                 ↓                              ↓
        POSIX regex grep                  Extract functions           Cross-encoder scoring
        (parallel, libc)                  & classes from AST          (batched inference)
```

**Performance note**: For literal patterns (no regex metacharacters), the scanner uses SIMD-optimized string search via Mojo's `String.find()`. For regex patterns, it falls back to POSIX regex (libc). The literal fast path is ~5-10x faster than regex for simple queries like `"handleError"` or `"def foo"`.

| Stage | Implementation |
|-------|----------------|
| Scanner | `src/scanner/_scanner.mojo` (Python extension) + `c_regex.mojo` |
| Extraction | `src/hygrep/extractor.py` (Tree-sitter AST) |
| Reranking | `src/hygrep/reranker.py` (ONNX batched) |

## Project Structure

```
src/
├── scanner/
│   ├── _scanner.mojo   # Python extension module (scan function)
│   └── c_regex.mojo    # POSIX regex FFI (libc)
├── hygrep/
│   ├── __init__.py     # Package version
│   ├── cli.py          # Python CLI entry point
│   ├── extractor.py    # Tree-sitter extraction
│   └── reranker.py     # ONNX cross-encoder
│   └── _scanner.so     # Built extension (gitignored)
tests/                  # Mojo + Python tests
pyproject.toml          # Python packaging
hatch_build.py          # Platform wheel hook
```

## Technology Stack

| Component | Version | Notes |
|-----------|---------|-------|
| Mojo | 25.7.* | Via MAX package |
| Python | >=3.11, <3.14 | CLI + inference |
| ONNX Runtime | >=1.16 | Model execution |
| Tree-sitter | >=0.24 | AST parsing (22 languages) |
| Model | mxbai-rerank-xsmall-v1 | INT8 quantized, ~40MB |

## Mojo Patterns

### Python Extension Modules

Build Mojo as native Python extension (no subprocess overhead):

```mojo
from python import Python, PythonObject
from python.bindings import PythonModuleBuilder

@export
fn PyInit__scanner() -> PythonObject:
    try:
        var b = PythonModuleBuilder("_scanner")
        b.def_function[scan]("scan", docstring="...")
        return b.finalize()
    except e:
        return abort[PythonObject](String("failed: ", e))

@export
fn scan(root: PythonObject, pattern: PythonObject) raises -> PythonObject:
    # Return Python dict of matches
    var result = Python.evaluate("{}")
    # ... scan logic ...
    return result
```

Build: `mojo build src/scanner/_scanner.mojo --emit shared-lib -o src/hygrep/_scanner.so`

### FFI for C Interop

```mojo
from sys.ffi import c_char, c_int, external_call

fn regcomp(
    preg: UnsafePointer[regex_t],
    pattern: UnsafePointer[c_char],
    cflags: c_int,
) -> c_int:
    return external_call["regcomp", c_int](preg, pattern, cflags)
```

### Memory Management

```mojo
var buffer = alloc[UInt8](size)
defer: buffer.free()
```

### Parallel Patterns

```mojo
@parameter
fn worker(i: Int):
    result[i] = process(items[i])

parallelize[worker](num_items)
```

## Code Standards

| Aspect | Standard |
|--------|----------|
| Formatting | `mojo format` (automatic) |
| Imports | stdlib → external → local |
| Functions | Docstrings on public APIs |
| Memory | Explicit cleanup, no leaks |
| Errors | `raises` for recoverable, `abort` for fatal |

## Verification

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Build | `pixi run build-ext` | Zero errors |
| Test | `pixi run test` | All pass |
| Smoke | `pixi run hygrep "test" ./src` | Returns results |
| Wheel | `uv build --wheel` | Platform-tagged wheel |

## Release to PyPI

**DO NOT trigger release workflow unless user explicitly says "publish to PyPI".**

Prerequisites (one-time):
1. Configure PyPI trusted publishing at https://pypi.org/manage/account/publishing/
2. Add pending publisher: project=`hygrep`, owner=`nijaru`, repo=`hygrep`, workflow=`release.yml`

To release:
```bash
gh workflow run release.yml -f version=X.Y.Z
```

Or via GitHub UI: Actions → Release → Run workflow → Enter version

## AI Context

**Read order:** `ai/STATUS.md` → `ai/DECISIONS.md`

| File | Purpose |
|------|---------|
| `ai/STATUS.md` | Current state, blockers |
| `ai/DECISIONS.md` | Architectural decisions |

## External References

- Mojo stdlib patterns: `~/github/modular/modular/mojo/stdlib/`
- Python extensions: `~/github/modular/modular/mojo/integration-test/python-extension-modules/`
