# Python extension module for hygrep scanner
# Build: mojo build src/scanner/_scanner.mojo --emit shared-lib -o src/hygrep/_scanner.so

from pathlib import Path
from collections import List, Set
from algorithm import parallelize
from memory import UnsafePointer, alloc
from os import abort
from os.path import realpath
from python import Python, PythonObject
from python.bindings import PythonModuleBuilder
from src.scanner.c_regex import Regex


# ============================================================================
# Pattern Detection
# ============================================================================


fn is_literal_pattern(pattern: String) -> Bool:
    """Check if pattern contains no regex metacharacters.

    If True, we can use fast SIMD string search instead of regex.
    """
    for i in range(len(pattern)):
        var c = pattern[i]
        # Common regex metacharacters
        if c == "*" or c == "+" or c == "?" or c == "." or c == "^":
            return False
        if c == "$" or c == "[" or c == "]" or c == "(" or c == ")":
            return False
        if c == "{" or c == "}" or c == "|" or c == "\\":
            return False
    return True


fn to_lower_ascii(s: String) -> String:
    """Fast ASCII-only lowercase. Sufficient for code identifiers."""
    var result = String(capacity=len(s))
    for i in range(len(s)):
        var c = ord(s[i])
        # ASCII uppercase A-Z (65-90) -> lowercase a-z (97-122)
        if c >= 65 and c <= 90:
            result += chr(c + 32)
        else:
            result += s[i]
    return result


# ============================================================================
# Python Extension Module Entry Point
# ============================================================================


@export
fn PyInit__scanner() -> PythonObject:
    """Create the _scanner Python extension module."""
    try:
        var b = PythonModuleBuilder("_scanner")
        b.def_function[scan](
            "scan",
            docstring=(
                "Scan directory for files matching pattern. Returns dict {path:"
                " content}."
            ),
        )
        return b.finalize()
    except e:
        return abort[PythonObject](
            String("failed to create _scanner module: ", e)
        )


# ============================================================================
# Exported Functions
# ============================================================================


@export
fn scan(
    root_obj: PythonObject,
    pattern_obj: PythonObject,
    include_hidden_obj: PythonObject = False,
) raises -> PythonObject:
    """
    Scan directory tree for files matching regex pattern.

    Args:
        root_obj: Root directory path (str)
        pattern_obj: Regex pattern to match (str)
        include_hidden_obj: Whether to include hidden files (bool, default False)

    Returns:
        Python dict mapping file paths to their contents
    """
    var root = Path(String(root_obj))
    var pattern = String(pattern_obj)
    var include_hidden = Bool(include_hidden_obj)

    # Validate root
    if not root.exists():
        raise Error("Path does not exist: " + String(root))
    if not root.is_dir():
        raise Error("Path is not a directory: " + String(root))

    # Run the scan
    var matches = hyper_scan(root, pattern, include_hidden)

    # Convert to Python dict (skip any files that fail UTF-8 conversion)
    var result = Python.evaluate("{}")
    for i in range(len(matches)):
        try:
            var path_str = String(matches[i].path)
            result[path_str] = matches[i].content
        except:
            # Skip files with encoding issues
            pass

    return result


# ============================================================================
# Scanner Implementation (adapted from walker.mojo)
# ============================================================================


@fieldwise_init
struct ScanMatch(Copyable, Movable):
    var path: Path
    var content: String

    fn __copyinit__(out self, existing: Self):
        self.path = existing.path
        self.content = existing.content

    fn __moveinit__(out self, deinit existing: Self):
        self.path = existing.path^
        self.content = existing.content^


fn is_ignored_dir(name: String) -> Bool:
    if name == "node_modules":
        return True
    if name == "target":
        return True
    if name == "build":
        return True
    if name == "dist":
        return True
    if name == "venv":
        return True
    if name == "env":
        return True
    if name == ".git":
        return True
    if name == ".pixi":
        return True
    if name == ".vscode":
        return True
    if name == ".idea":
        return True
    if name == "__pycache__":
        return True
    return False


fn is_binary_ext(name: String) -> Bool:
    # Compiled/object files
    if name.endswith(".pyc"):
        return True
    if name.endswith(".pyo"):
        return True
    if name.endswith(".o"):
        return True
    if name.endswith(".so"):
        return True
    if name.endswith(".dylib"):
        return True
    if name.endswith(".dll"):
        return True
    if name.endswith(".bin"):
        return True
    if name.endswith(".exe"):
        return True
    if name.endswith(".a"):
        return True
    if name.endswith(".lib"):
        return True
    # Archives
    if name.endswith(".zip"):
        return True
    if name.endswith(".tar"):
        return True
    if name.endswith(".gz"):
        return True
    if name.endswith(".bz2"):
        return True
    if name.endswith(".xz"):
        return True
    if name.endswith(".7z"):
        return True
    if name.endswith(".rar"):
        return True
    if name.endswith(".jar"):
        return True
    if name.endswith(".war"):
        return True
    if name.endswith(".whl"):
        return True
    # Documents/media
    if name.endswith(".pdf"):
        return True
    if name.endswith(".doc"):
        return True
    if name.endswith(".docx"):
        return True
    if name.endswith(".xls"):
        return True
    if name.endswith(".xlsx"):
        return True
    if name.endswith(".ppt"):
        return True
    if name.endswith(".pptx"):
        return True
    # Images
    if name.endswith(".png"):
        return True
    if name.endswith(".jpg"):
        return True
    if name.endswith(".jpeg"):
        return True
    if name.endswith(".gif"):
        return True
    if name.endswith(".ico"):
        return True
    if name.endswith(".svg"):
        return True
    if name.endswith(".webp"):
        return True
    if name.endswith(".bmp"):
        return True
    if name.endswith(".tiff"):
        return True
    # Audio/video
    if name.endswith(".mp3"):
        return True
    if name.endswith(".mp4"):
        return True
    if name.endswith(".wav"):
        return True
    if name.endswith(".avi"):
        return True
    if name.endswith(".mov"):
        return True
    if name.endswith(".mkv"):
        return True
    # Data files
    if name.endswith(".db"):
        return True
    if name.endswith(".sqlite"):
        return True
    if name.endswith(".sqlite3"):
        return True
    if name.endswith(".pickle"):
        return True
    if name.endswith(".pkl"):
        return True
    if name.endswith(".npy"):
        return True
    if name.endswith(".npz"):
        return True
    if name.endswith(".onnx"):
        return True
    if name.endswith(".pt"):
        return True
    if name.endswith(".pth"):
        return True
    if name.endswith(".safetensors"):
        return True
    # Lock files
    if name.endswith(".lock"):
        return True
    if name.endswith("-lock.json"):
        return True
    return False


alias MAX_FILE_SIZE = 1_000_000  # 1MB limit


fn is_likely_binary(content: String) -> Bool:
    """Check if content appears to be binary (contains null bytes)."""
    for i in range(min(len(content), 8192)):
        if ord(content[i]) == 0:
            return True
    return False


fn scan_file_with_content(file: Path, re: Regex) -> String:
    """Returns file content if regex matches, empty string if not."""
    try:
        var stat = file.stat()
        if stat.st_size > MAX_FILE_SIZE:
            return ""

        with open(file, "r") as f:
            var content = f.read()
            # Skip binary files that slipped through extension check
            if is_likely_binary(content):
                return ""
            if re.matches(content):
                return content
            return ""
    except:
        return ""


fn scan_file_literal(file: Path, pattern_lower: String) -> String:
    """Returns file content if literal pattern matches (case-insensitive).

    Uses SIMD-optimized String.find() instead of regex for ~5-10x speedup
    on literal patterns.
    """
    try:
        var stat = file.stat()
        if stat.st_size > MAX_FILE_SIZE:
            return ""

        with open(file, "r") as f:
            var content = f.read()
            # Skip binary files that slipped through extension check
            if is_likely_binary(content):
                return ""
            # Case-insensitive match: convert content to lowercase
            var content_lower = to_lower_ascii(content)
            # String.find() uses SIMD _memmem internally
            if content_lower.find(pattern_lower) >= 0:
                return content  # Return original content, not lowercased
            return ""
    except:
        return ""


fn hyper_scan(
    root: Path, pattern: String, include_hidden: Bool = False
) raises -> List[ScanMatch]:
    var candidates = List[ScanMatch]()
    var all_files = List[Path]()
    var visited = Set[String]()

    # 1. Collect files
    var stack = List[Path]()
    stack.append(root)

    while len(stack) > 0:
        var current = stack.pop()
        if current.is_dir():
            try:
                var real = realpath(current)
                if real in visited:
                    continue
                visited.add(real)
            except:
                pass

            try:
                var entries = current.listdir()
                for i in range(len(entries)):
                    var entry = entries[i]
                    var full_path = current / entry
                    var name_str = entry.name()

                    # Skip hidden files unless --hidden flag
                    if not include_hidden and name_str.startswith("."):
                        continue

                    if full_path.is_dir():
                        if is_ignored_dir(name_str):
                            continue
                        stack.append(full_path)
                    else:
                        if is_binary_ext(name_str):
                            continue
                        all_files.append(full_path)
            except:
                continue
        else:
            all_files.append(current)

    var num_files = len(all_files)
    if num_files == 0:
        return candidates^

    # 2. Parallel scan - choose fast path for literals
    var use_literal = is_literal_pattern(pattern)
    var mask = alloc[Bool](num_files)
    var contents = List[String](capacity=num_files)

    for i in range(num_files):
        mask[i] = False
        contents.append("")

    if use_literal:
        # Fast path: SIMD string search (case-insensitive)
        var pattern_lower = to_lower_ascii(pattern)

        @parameter
        fn literal_worker(i: Int):
            var result = scan_file_literal(all_files[i], pattern_lower)
            if len(result) > 0:
                mask[i] = True
                contents[i] = result
            else:
                mask[i] = False

        parallelize[literal_worker](num_files)
    else:
        # Regex path: POSIX regex matching
        var re = Regex(pattern)

        @parameter
        fn regex_worker(i: Int):
            var result = scan_file_with_content(all_files[i], re)
            if len(result) > 0:
                mask[i] = True
                contents[i] = result
            else:
                mask[i] = False

        parallelize[regex_worker](num_files)

    # 3. Gather results
    for i in range(num_files):
        if mask[i]:
            candidates.append(ScanMatch(all_files[i], contents[i]))

    mask.free()

    return candidates^
