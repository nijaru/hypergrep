from tokenizers import Tokenizer
import numpy as np

class RerankTokenizer:
    def __init__(self, path):
        self.tokenizer = Tokenizer.from_file(path)
        self.tokenizer.enable_padding(length=512)
        self.tokenizer.enable_truncation(max_length=512)

    def prepare_inputs(self, query, candidates):
        pairs = [(query, c) for c in candidates]
        encodings = self.tokenizer.encode_batch(pairs)
        
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)
        
        return input_ids, attention_mask, token_type_ids