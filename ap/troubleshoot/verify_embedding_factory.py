import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ap.utils.embedding_factory import embedding_factory

def test_factory():
    print(f"Testing EmbeddingFactory...")
    print(f"Device: {embedding_factory.device}")
    
    text = "Hello, world!"
    embedding = embedding_factory.get_embedding(text)
    
    print(f"Embedding generated for '{text}'")
    print(f"Embedding length: {len(embedding)}")
    print(f"First 5 dimensions: {embedding[:5]}")
    
    if len(embedding) == 256:
        print("SUCCESS: Embedding dimension is 256.")
    else:
        print(f"FAILURE: Expected 256 dimensions, got {len(embedding)}")

if __name__ == "__main__":
    test_factory()
