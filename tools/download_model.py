from huggingface_hub import hf_hub_download
import os
import shutil

MODEL_REPO = "mixedbread-ai/mxbai-rerank-xsmall-v1"
MODEL_FILE = "onnx/model_quantized.onnx" 
TOKENIZER_FILE = "tokenizer.json"
DEST_DIR = "models"

def download_model():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    print(f"Downloading {MODEL_REPO}...")
    
    try:
        model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
        tokenizer_path = hf_hub_download(repo_id=MODEL_REPO, filename=TOKENIZER_FILE)
        
        shutil.copy(model_path, os.path.join(DEST_DIR, "reranker.onnx"))
        shutil.copy(tokenizer_path, os.path.join(DEST_DIR, "tokenizer.json"))
        
        print("Model downloaded successfully to models/reranker.onnx")
    except Exception as e:
        print(f"Error downloading model: {e}")

if __name__ == "__main__":
    download_model()
