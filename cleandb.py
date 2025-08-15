import os
import shutil

def reset_indexes():
    """Delete FAISS index and metadata database files to reset the system."""
    
    # Define paths
    metadata_db_path = "rag_system/data/metadata.db"
    faiss_index_path = "rag_system/data/indexes/index.faiss"
    
    # Delete metadata database if it exists
    if os.path.exists(metadata_db_path):
        try:
            os.remove(metadata_db_path)
            print(f"Deleted: {metadata_db_path}")
        except Exception as e:
            print(f"Error deleting {metadata_db_path}: {e}")
    
    # Delete FAISS index if it exists
    if os.path.exists(faiss_index_path):
        try:
            os.remove(faiss_index_path)
            print(f"Deleted: {faiss_index_path}")
        except Exception as e:
            print(f"Error deleting {faiss_index_path}: {e}")
    
    print("Index reset complete.")

if __name__ == "__main__":
    reset_indexes()