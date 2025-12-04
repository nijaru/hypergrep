"""Embedder - ONNX text embeddings for semantic search."""

import os

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

# Suppress ONNX Runtime warnings
ort.set_default_logger_severity(3)

# all-MiniLM-L6-v2: small (80MB), fast, 384 dimensions
MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_FILE = "onnx/model.onnx"
TOKENIZER_FILE = "tokenizer.json"
DIMENSIONS = 384


class Embedder:
    """Generate text embeddings using ONNX model."""

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = cache_dir
        self._session: ort.InferenceSession | None = None
        self._tokenizer: Tokenizer | None = None

    def _ensure_loaded(self) -> None:
        """Lazy load model and tokenizer."""
        if self._session is not None:
            return

        # Download model files
        model_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            cache_dir=self.cache_dir,
        )
        tokenizer_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=TOKENIZER_FILE,
            cache_dir=self.cache_dir,
        )

        # Load tokenizer
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=512)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

        # Load ONNX model
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = os.cpu_count() or 4

        self._session = ort.InferenceSession(
            model_path,
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), 384) with normalized embeddings.
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, DIMENSIONS)

        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._session is not None

        # Tokenize
        encoded = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)

        # Run inference
        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )

        # Mean pooling over token embeddings
        token_embeddings = outputs[0]  # (batch, seq_len, hidden_size)
        mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.sum(mask_expanded, axis=1)
        embeddings = sum_embeddings / np.maximum(sum_mask, 1e-9)

        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-9)

        return embeddings.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        return self.embed([text])[0]
