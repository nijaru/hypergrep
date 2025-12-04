# Roadmap

## v1: Grep + Rerank (Complete)

Stateless code search: regex scanning → cross-encoder reranking.

| Phase          | Status | Key Features                                        |
| -------------- | ------ | --------------------------------------------------- |
| 1-4 MVP        | ✅     | Mojo scanner, ONNX reranker, Tree-sitter extraction |
| 5 Distribution | ✅     | Python extension module, PyPI wheels                |
| 6 Performance  | ✅     | Parallel scanning (~20k files/sec), --fast mode     |
| 7 CLI Polish   | ✅     | Colors, gitignore, context lines, completions       |
| 8 Hardening    | ✅     | Model validation, error handling, 22 languages      |
| 9 Release      | ✅     | v0.0.6 on PyPI                                      |

## v2: Semantic-First (In Progress)

Reimagining hhg as pure semantic code search.

**Branch:** `experiment/semantic-search`

### Phase 1: Core Refactor

| Task         | Bead      | Status     | Description                   |
| ------------ | --------- | ---------- | ----------------------------- |
| CLI Refactor | hgrep-xwd | 🔴 Ready   | Main search flow → semantic   |
| Auto-index   | hgrep-mb9 | ⏳ Blocked | Build index on first query    |
| Auto-update  | hgrep-43j | ⏳ Blocked | Incremental update when stale |

### Phase 2: Polish

| Task           | Bead      | Status     | Description                                  |
| -------------- | --------- | ---------- | -------------------------------------------- |
| Escape hatches | hgrep-9go | ⏳ Blocked | -e (exact), -r (regex) flags                 |
| Drop reranker  | hgrep-zlf | ⏳ Blocked | Remove cross-encoder (embeddings sufficient) |
| Output format  | hgrep-dsr | ⏳ Blocked | Clean output with content preview            |

### Phase 3: Performance

| Task               | Status  | Description         |
| ------------------ | ------- | ------------------- |
| Parallel embedding | ❌ TODO | Batch + multithread |
| Index compression  | ❌ TODO | Reduce .hhg/ size   |
| Lazy loading       | ❌ TODO | Faster startup      |

## Key Changes v1 → v2

| Aspect       | v1                 | v2                      |
| ------------ | ------------------ | ----------------------- |
| Default mode | Grep + rerank      | Semantic search         |
| Index        | None (stateless)   | Auto-managed .hhg/      |
| Reranking    | Cross-encoder      | Dropped (embeddings)    |
| Flags        | --fast, --semantic | -e, -r (escape hatches) |
| First use    | Instant            | Auto-builds index       |

## Non-Goals

- ~~Indexing/persistence~~ → Now core feature
- Background daemon (auto-update is enough)
- Custom model training
- Server mode
