# app/chatbot/vector_store.py
import os
import json
import sqlite3
import threading
from typing import List, Tuple, Dict, Optional

import numpy as np
import hnswlib
from sentence_transformers import SentenceTransformer

from app.config import settings

# Paths for persistence
INDEX_DIR = os.path.join(os.path.dirname(__file__), "kb_index")
os.makedirs(INDEX_DIR, exist_ok=True)
INDEX_PATH = os.path.join(INDEX_DIR, "hnsw_index.bin")
META_PATH = os.path.join(INDEX_DIR, "meta.json")
VECTORS_PATH = os.path.join(INDEX_DIR, "vectors.npy")

# Configs
EMBEDDING_MODEL = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DIM = 384  # embedding dim for all-MiniLM-L6-v2
SPACE = "l2"
M = 32
EF_CONSTRUCTION = 200
EF_SEARCH = 50
TOP_K_DEFAULT = 3

_lock = threading.Lock()


class KBVectorStore:
    """
    Builds a vector index from the normalized KB (SQLite) and serves searches.
    - Builds on first query (lazy) unless build_index() is called manually.
    - Persists index + metadata to disk.
    """

    def __init__(self, db_path: Optional[str] = None, index_path: str = INDEX_PATH, meta_path: str = META_PATH):
        self.db_path = db_path or getattr(settings, "KB_DB_PATH", settings.KB_DB_PATH)
        self.index_path = index_path
        self.meta_path = meta_path
        self.model = SentenceTransformer(f"sentence-transformers/{EMBEDDING_MODEL}")
        self.dim = DIM
        self.index: Optional[hnswlib.Index] = None
        self.id_to_meta: Dict[int, dict] = {}
        self._loaded = False
        self._num_elements = 0

    # ---------------------
    # DB reading / document assembly
    # ---------------------
    def _fetch_all_diseases(self) -> List[dict]:
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT disease_id, name, description, red_flags, recommended_tests, suggested_measures, created_at FROM diseases")
        rows = cursor.fetchall()

        docs = []
        for row in rows:
            disease_id, name, description, red_flags, tests_json, measures_json, created_at = row
            # fetch related tables
            cursor.execute("SELECT symptom FROM symptoms WHERE disease_id = ?", (disease_id,))
            symptoms = [r[0] for r in cursor.fetchall()]

            cursor.execute("SELECT name, rxnorm_json, openfda_json FROM drugs WHERE disease_id = ?", (disease_id,))
            drugs = [{"name": r[0], "rxnorm": json.loads(r[1]) if r[1] else {}, "openfda": json.loads(r[2]) if r[2] else {}} for r in cursor.fetchall()]

            cursor.execute("SELECT test_name, details FROM tests WHERE disease_id = ?", (disease_id,))
            tests = [{"name": r[0], "details": r[1]} for r in cursor.fetchall()]

            cursor.execute("SELECT keyword FROM keywords WHERE disease_id = ?", (disease_id,))
            keywords = [r[0] for r in cursor.fetchall()]

            cursor.execute("SELECT source, url FROM disease_references WHERE disease_id = ?", (disease_id,))
            references = [{"source": r[0], "url": r[1]} for r in cursor.fetchall()]

            # recommended_tests / measures could be JSON in db; try to load
            try:
                recommended_tests_extra = json.loads(tests_json) if tests_json else []
            except Exception:
                recommended_tests_extra = []

            try:
                suggested_measures_extra = json.loads(measures_json) if measures_json else []
            except Exception:
                suggested_measures_extra = []

            docs.append({
                "disease_id": disease_id,
                "name": name,
                "description": description or "",
                "red_flags": red_flags or "",
                "symptoms": symptoms,
                "tests": tests + recommended_tests_extra,
                "measures": suggested_measures_extra + measures_json if isinstance(suggested_measures_extra, list) else suggested_measures_extra,
                "drugs": drugs,
                "keywords": keywords,
                "references": references,
                "created_at": created_at
            })
        conn.close()
        return docs

    def _make_documents(self, disease_entry: dict) -> Tuple[str, str]:
        """
        Returns (short_summary, detailed_text)
        short_summary: 1-3 lines
        detailed_text: concatenated structured sections
        """
        name = disease_entry.get("name", "")
        desc = disease_entry.get("description", "")
        symptoms = disease_entry.get("symptoms", []) or []
        tests = disease_entry.get("tests", []) or []
        measures = disease_entry.get("measures", []) or []
        keywords = disease_entry.get("keywords", []) or []

        # short summary: name + first 200 chars of description + first symptom if any
        summary_parts = [name]
        if desc:
            summary_parts.append((desc.strip()[:250] + ("..." if len(desc) > 250 else "")))
        if symptoms:
            summary_parts.append("Symptoms: " + (symptoms[0][:120] + ("..." if len(symptoms[0]) > 120 else "")))
        short_summary = " | ".join([p for p in summary_parts if p])

        # detailed context: structured with headings
        detailed = [f"Disease: {name}", f"Description: {desc}"]
        if symptoms:
            detailed.append("Symptoms:")
            detailed.extend([f"- {s}" for s in symptoms])
        if tests:
            detailed.append("Recommended Tests:")
            for t in tests:
                if isinstance(t, dict):
                    detailed.append(f"- {t.get('name','')} : {t.get('details','')}")
                else:
                    detailed.append(f"- {t}")
        if measures:
            detailed.append("Suggested Measures:")
            if isinstance(measures, list):
                detailed.extend([f"- {m}" for m in measures])
            else:
                detailed.append(str(measures))
        if keywords:
            detailed.append("Keywords: " + ", ".join(keywords))
        if disease_entry.get("references"):
            detailed.append("References:")
            detailed.extend([f"- {r.get('source','')} {r.get('url','')}" for r in disease_entry.get("references", [])])

        detailed_text = "\n".join(detailed)
        return short_summary, detailed_text

    # ---------------------
    # Index build / persistence
    # ---------------------
    def build_index(self, rebuild: bool = False) -> None:
        """
        Build or rebuild the HNSW index from the SQLite KB.
        """
        with _lock:
            docs = self._fetch_all_diseases()
            if not docs:
                print("[KBVectorStore] No diseases found in KB DB at", self.db_path)
                return

            # Create texts (detailed) to embed
            metas = []
            texts = []
            for i, d in enumerate(docs):
                short, detailed = self._make_documents(d)
                metas.append({
                    "id": d["disease_id"],
                    "name": d["name"],
                    "short": short
                })
                texts.append(detailed)

            # Encode embeddings
            print("[KBVectorStore] Encoding embeddings for", len(texts), "documents...")
            vectors = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

            # Save vectors & metadata
            np.save(VECTORS_PATH, vectors)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({"metas": metas}, f, ensure_ascii=False, indent=2)

            # Initialize HNSW index
            p = hnswlib.Index(space=SPACE, dim=self.dim)
            p.init_index(max_elements=len(vectors), ef_construction=EF_CONSTRUCTION, M=M)
            p.add_items(vectors, np.arange(len(vectors)))
            p.set_ef(EF_SEARCH)
            p.save_index(self.index_path)

            # assign to instance
            self.index = p
            self.id_to_meta = {i: metas[i] for i in range(len(metas))}
            self._num_elements = len(vectors)
            self._loaded = True
            print("[KBVectorStore] Index built and saved:", self.index_path)

    def _load_index(self) -> bool:
        """
        Try to load index + meta from disk. Returns True on success.
        """
        if not (os.path.exists(self.index_path) and os.path.exists(self.meta_path) and os.path.exists(VECTORS_PATH)):
            return False
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                metas = meta.get("metas", [])
            self.id_to_meta = {i: metas[i] for i in range(len(metas))}
            vectors = np.load(VECTORS_PATH)
            p = hnswlib.Index(space=SPACE, dim=self.dim)
            p.load_index(self.index_path)
            p.set_ef(EF_SEARCH)
            self.index = p
            self._num_elements = vectors.shape[0]
            self._loaded = True
            return True
        except Exception as e:
            print("[KBVectorStore] Failed to load index:", e)
            return False

    # ---------------------
    # Search
    # ---------------------
    def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> List[dict]:
        """
        Returns list of dicts: { 'disease_id', 'name', 'short', 'score', 'detailed' }
        """
        # ensure index available
        if not self._loaded:
            ok = self._load_index()
            if not ok:
                # lazy build
                print("[KBVectorStore] Index not found on disk. Building now (lazy)...")
                self.build_index()
                if not self._loaded:
                    # fallback: return empty
                    return []

        q_vec = self.model.encode([query], convert_to_numpy=True)
        labels, distances = self.index.knn_query(q_vec, k=top_k)
        results = []
        for rank, (label, dist) in enumerate(zip(labels[0], distances[0])):
            meta = self.id_to_meta.get(int(label), {})
            # For detailed text, we can reassemble from DB using disease id
            detailed = self._get_detailed_by_disease_id(meta.get("id"))
            results.append({
                "disease_id": meta.get("id"),
                "name": meta.get("name"),
                "short": meta.get("short"),
                "score": float(dist),
                "detailed": detailed
            })
        return results

    def _get_detailed_by_disease_id(self, disease_id: str) -> str:
        """
        Reconstruct the detailed text for a single disease from DB (same format used in build).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT disease_id, name, description FROM diseases WHERE disease_id = ?", (disease_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return ""
        disease_id, name, description = row
        # fetch symptoms/tests/measures/references
        c.execute("SELECT symptom FROM symptoms WHERE disease_id = ?", (disease_id,))
        symptoms = [r[0] for r in c.fetchall()]

        c.execute("SELECT test_name, details FROM tests WHERE disease_id = ?", (disease_id,))
        tests = [{"name": r[0], "details": r[1]} for r in c.fetchall()]

        c.execute("SELECT keyword FROM keywords WHERE disease_id = ?", (disease_id,))
        keywords = [r[0] for r in c.fetchall()]

        c.execute("SELECT source, url FROM disease_references WHERE disease_id = ?", (disease_id,))
        references = [{"source": r[0], "url": r[1]} for r in c.fetchall()]

        conn.close()

        parts = [f"Disease: {name}", f"Description: {description or ''}"]
        if symptoms:
            parts.append("Symptoms:")
            parts.extend([f"- {s}" for s in symptoms])
        if tests:
            parts.append("Recommended Tests:")
            for t in tests:
                parts.append(f"- {t.get('name','')}: {t.get('details','')}")
        if keywords:
            parts.append("Keywords: " + ", ".join(keywords))
        if references:
            parts.append("References:")
            parts.extend([f"- {r.get('source','')} {r.get('url','')}" for r in references])
        return "\n".join(parts)
