import pickle
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

INDEX_FILE = Path("code_index.faiss")
META_FILE  = Path("code_meta.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"

class SemanticCodeLinker:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: str = "cpu"            # new parameter
    ):
        # device should be "cpu" or "cuda"
        self.model = SentenceTransformer(model_name, device=device)
        self.index: Optional[faiss.Index] = None  # type: ignore
        self.metadata: List[Tuple[Path, int, str]] = []

    def build_index(
        self,
        code_dir: Path,
        rebuild: bool = False,
        progress_cb: Optional[Callable[[int], None]] = None,
        batch_size: int = 128
    ):
        """
        Walk every file under code_dir, collect non-empty lines as snippets,
        compute embeddings in batches (on the chosen device),
        build & save a FAISS index + metadata.
        Calls progress_cb(percent) if provided after each batch.
        """
        if INDEX_FILE.exists() and META_FILE.exists() and not rebuild:
            self.index = faiss.read_index(str(INDEX_FILE))
            with open(META_FILE, "rb") as f:
                self.metadata = pickle.load(f)
            return

        snippets = []
        meta = []
        for file in code_dir.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in {".py",".js",".java",".cpp",".cs",".ts"}:
                continue
            for lineno, line in enumerate(file.open(errors="ignore"), start=1):
                text = line.strip()
                if text:
                    snippets.append(text)
                    meta.append((file, lineno, text))

        total = len(snippets)
        embs_list = []
        for i in range(0, total, batch_size):
            batch = snippets[i : i + batch_size]
            # this will run on GPU if model was constructed with device="cuda"
            emb = self.model.encode(batch, convert_to_numpy=True)
            embs_list.append(np.array(emb, dtype="float32"))
            if progress_cb:
                pct = int(min(100, (i + batch_size) / total * 100))
                progress_cb(pct)

        embs = np.vstack(embs_list)
        dim = embs.shape[1]
        idx = faiss.IndexFlatL2(dim)
        idx.add(embs)  # type: ignore

        faiss.write_index(idx, str(INDEX_FILE))
        with open(META_FILE, "wb") as f:
            pickle.dump(meta, f)

        self.index = idx
        self.metadata = meta

    def query(
        self,
        text: str,
        top_k: int = 5
    ) -> List[Tuple[Path, int, str, float]]:
        """
        Encode `text` (on chosen device), search the index,
        and return top_k matches as (file, lineno, snippet, distance).
        """
        if self.index is None or not self.metadata:
            raise RuntimeError("Index not built yet. Call build_index() first.")

        emb = self.model.encode([text], convert_to_numpy=True)
        emb32 = np.array(emb, dtype="float32")
        distances, indices = self.index.search(emb32, top_k)  # type: ignore

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            file, lineno, snippet = self.metadata[idx]
            results.append((file, lineno, snippet, float(dist)))
        return results
