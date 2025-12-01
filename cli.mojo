from src.scanner.walker import hyper_scan
from src.inference.reranker import Reranker
from pathlib import Path
import sys

fn main() raises:
    var args = sys.argv()
    if len(args) < 3:
        print("Usage: hygrep <pattern> <path>")
        return

    var pattern = args[1]
    var path_str = args[2]
    var root = Path(path_str)
    
    print("HyperGrep: Searching for '" + pattern + "' in " + path_str)
    
    # 1. Recall (Scanner)
    var matches = hyper_scan(root, pattern)
    print("Recall: Found " + String(len(matches)) + " candidates.")
    
    if len(matches) == 0:
        return

    # 2. Rerank (Brain)
    print("Reranking...")
    var brain = Reranker()
    
    var match_strings = List[String]()
    for i in range(len(matches)):
        match_strings.append(String(matches[i]))
        
    var ranked_indices = brain.rerank(pattern, match_strings)
    
    print("\n--- Top Results ---")
    # Print top 10
    for i in range(min(10, len(ranked_indices))):
        var idx = ranked_indices[i]
        print(match_strings[idx])