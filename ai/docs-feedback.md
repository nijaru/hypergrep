# Documentation Feedback

Feedback from an AI agent learning when/how to use hhg vs grep.

## What's Clear

- Mode table (semantic/fast/exact/regex) is excellent
- Install and usage examples are good
- JSON output format is well documented

## What Could Be Clearer

### 1. The Key Differentiator

The README shows _how_ to use hhg but not _why_ it's better than grep in specific situations.

**Current:** "Search your codebase using natural language"

**Clearer:** "Find code that implements a concept, not just text that mentions it"

**Example that would help:**

```
# grep finds comments MENTIONING "error handling"
$ grep "error handling" ./src
./src/lib.rs:// TODO: improve error handling

# hhg finds code IMPLEMENTING error handling
$ hhg "error handling" ./src
src/lib.rs:24 function convert_error
  fn convert_error(err: anyhow::Error) -> Error { ... }
```

This shows the fundamental difference: hhg returns _implementations_, grep returns _text matches_.

### 2. When to Use Each Mode

The mode table shows flags but not decision criteria:

| I want to...                     | Use                             |
| -------------------------------- | ------------------------------- |
| Find code implementing a concept | `hhg "concept"` (default)       |
| Quick semantic search, no index  | `hhg -f "query"`                |
| Find exact string like `TODO`    | `hhg -e "TODO"` or `grep`       |
| Pattern match                    | `hhg -r "pattern"` or `grep -E` |

### 3. What "Semantic" Means in Practice

The term "semantic search" is abstract. Concrete examples help:

- `hhg "authentication"` → finds `login()`, `verify_token()`, `session_create()`
- `hhg "error handling"` → finds `convert_error()`, `handle_failure()`, `ErrorKind`
- `hhg "database"` → finds `Connection`, `query()`, `execute()`

### 4. Index Behavior

Not immediately clear:

- Where is the index stored? (`.hhg/`)
- When does it auto-rebuild?
- Can I check if index is current?

`hhg status` exists but isn't prominent in the docs.

## Suggested README Changes

### Add "Why hhg?" section after intro:

```markdown
## Why hhg over grep?

grep finds text. hhg finds code.

| Query            | grep finds                | hhg finds                   |
| ---------------- | ------------------------- | --------------------------- |
| "error handling" | Comments mentioning it    | `convert_error()` function  |
| "authentication" | Strings containing "auth" | `login()`, `verify_token()` |

Use grep for exact strings (`TODO`, `FIXME`, import statements).
Use hhg when you want the implementation, not mentions.
```

## Overall

The tool works well. The docs explain _how_ but could better explain _when_ and _why_. The key insight—"finds implementations, not mentions"—should be front and center.
