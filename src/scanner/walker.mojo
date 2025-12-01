from pathlib import Path
from collections import List
from src.scanner.py_regex import Regex

fn scan_file(file: Path, re: Regex) -> Bool:
    try:
        with open(file, "r") as f:
            var content = f.read()
            return re.matches(content)
    except:
        return False

fn hyper_scan(root: Path, pattern: String) raises -> List[Path]:
    var candidates = List[Path]()
    var all_files = List[Path]()
    
    var stack = List[Path]()
    stack.append(root)

    while len(stack) > 0:
        var current = stack.pop()
        if current.is_dir():
            try:
                var entries = current.listdir()
                for i in range(len(entries)):
                    var entry = entries[i]
                    if entry.name().startswith("."):
                        continue
                        
                    if entry.is_dir():
                        stack.append(entry)
                    else:
                        all_files.append(entry)
            except:
                continue
        else:
            all_files.append(current)

    print("Scanned " + String(len(all_files)) + " files.")

    var re = Regex(pattern)
    
    for i in range(len(all_files)):
        if scan_file(all_files[i], re):
            candidates.append(all_files[i])
            
    return candidates^
