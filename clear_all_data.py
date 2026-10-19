"""
clear_all_data.py
Clears ALL stored data: ChromaDB collections, SQLite FTS5 index,
flashrank_cache, and chroma_cache. Does NOT touch any source code files.
"""

import os
import shutil
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_ROOTS = list(dict.fromkeys([WORKSPACE_ROOT, SCRIPT_DIR]))

for directory_name, label in [
    ("chroma_kb", "ChromaDB knowledge base"),
    ("chroma_cache", "ChromaDB semantic cache"),
    ("flashrank_cache", "FlashRank model cache"),
]:
    print(f"Clearing {label}...")
    found = False
    for data_root in DATA_ROOTS:
        path = os.path.join(data_root, directory_name)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"  Deleted {path}")
            found = True
    if not found:
        print("  No matching directories found, skipping.")

print("Clearing SQLite FTS5 indexes...")
for data_root in DATA_ROOTS:
    db_path = os.path.join(data_root, "fts5_index.db")
    if not os.path.exists(db_path):
        continue
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM kb_fts")
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
        print(f"  Cleared {db_path}")
    except sqlite3.OperationalError as exc:
        print(f"  Could not clear {db_path}: {exc}")
    finally:
        conn.close()

print(
    "\nAll targeted app data cleared. Source files and unrelated databases are untouched."
)
print("To re-index documents, run: python add_documents.py")
