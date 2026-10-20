import os
import add_documents

def auto_seed_knowledge_base():
    """
    Automatically indexes the 50-page enterprise manual on container boot
    if ChromaDB is not yet populated.
    """
    try:
        stats = add_documents.show_stats()
        current_chunks = stats.get("chroma_chunks", 0)
        print(f"Current Knowledge Base chunks: {current_chunks}")

        target_pdf = "TechMart_Enterprise_Operations_and_Support_Manual_50Pages.pdf"
        if os.path.exists(target_pdf):
            # Check if this specific document is already loaded
            existing_docs = [d.get("source") for d in add_documents.list_documents()]
            if target_pdf not in existing_docs:
                print(f"Auto-indexing {target_pdf} into ChromaDB and SQLite FTS5...")
                count = add_documents.add_pdf(target_pdf)
                print(f"Successfully auto-indexed {count} chunks from {target_pdf}!")
            else:
                print(f"{target_pdf} is already indexed ({current_chunks} chunks active).")
        else:
            print(f"Notice: {target_pdf} not found in root directory.")
    except Exception as e:
        print(f"Error during auto-seeding knowledge base: {e}")

if __name__ == "__main__":
    auto_seed_knowledge_base()
