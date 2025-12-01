# Mojo & MAX Project Reference

**Based on:** `modular/modular` repository analysis (Updated Nov 30, 2025).

## 1. Project Setup (Pixi)

The standard way to set up a Mojo project with AI dependencies is using `pixi`.

```toml
[workspace]
name = "hgrep"
version = "0.1.0"
description = "Agent-Native search tool"
channels = ["conda-forge", "https://conda.modular.com/max-nightly/", "pytorch"]
platforms = ["osx-arm64", "linux-64"]

[dependencies]
max = "*"
python = ">=3.11,<3.14"
onnxruntime = ">=1.16.0,<2"  # Fallback inference engine

[tasks]
build = "mojo build cli.mojo -o hygrep"
run = "mojo cli.mojo"
```

## 2. MAX Engine Architecture

The MAX Engine uses a **Graph-based architecture**.

### Key Components:
1.  **Mojo Graph Operations (`max.kernels`):** Low-level kernels registered via `@compiler.register`.
2.  **Python Graph API (`max.graph`):** Constructs the graph. currently NO public high-level Mojo Graph Construction API.
3.  **Execution:** Models are typically loaded/run via `max.engine.InferenceSession` (Python).

### "Single Static Binary" Reality
Since the high-level Graph API is Python-centric, the "standard" path for MAX + Mojo is **Hybrid**:
1.  **Python Interop:** Use `from python import Python` to import `max.engine` (or `onnxruntime`).
2.  **Execution:** Load and run the model from Mojo, driving the Python object.

**Decision for `hgrep`:**
We use **Python Interop**.
*   **Primary:** `onnxruntime` (via Python) for maximum compatibility and ease of shipping (Phase 2).
*   **Secondary:** `max.engine` (via Python) for performance on supported hardware.

## 3. Directory Structure
Recommended structure for `hgrep`:

```
hgrep/
├── pixi.toml             # Dependencies
├── src/
│   ├── cli.mojo          # Entry point
│   ├── scanner/          # "Hyper Scanner" (Mojo + Libc)
│   └── inference/        # AI Integration (Python Interop)
└── models/               # ONNX models
```

## 4. Mojo Standard Library (v0.26+ Changes)

**Critical Update:** `UnsafePointer` memory management has changed significantly in Nightly/v0.26+.

### Allocation
`UnsafePointer.alloc()` is **removed**. You must use the global `alloc` function.

```mojo
from memory import UnsafePointer, alloc

fn example():
    # OLD: var p = UnsafePointer[Int].alloc(10)
    
    # NEW: Use global alloc
    var p = alloc[Int](10)
    p[0] = 1
    p.free()
```

### FFI & C-Bindings
To bind C functions taking `void*` or `char*`:

```mojo
from sys import external_call
from memory import UnsafePointer

# Define VoidPtr as UnsafePointer to Byte
alias VoidPtr = UnsafePointer[Scalar[DType.uint8]]

fn call_c_func():
    # Cast or allocate
    var ptr = VoidPtr.alloc(10)
    external_call["c_func", NoneType](ptr)
```

## 5. Code Examples

### Python Interop (The "Standard" Way)
```mojo
from python import Python

fn rerank(query: String, candidates: List[String]) raises:
    # Import Engine via Python
    var ort = Python.import_module("onnxruntime")
    var session = ort.InferenceSession("models/reranker.onnx")
    
    # Execute
    var inputs = ... 
    var outputs = session.run(None, inputs)
```