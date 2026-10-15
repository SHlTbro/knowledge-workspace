# SPDX-License-Identifier: MIT
# Tokenization/BM25 adapted from llm-wiki-kit/.schema/search.py:
# https://github.com/xiaojian968/llm-wiki-kit
# commit cc32fd65314e2ed463743ebdc4cfc3f583be1b40, via Vault 3 scripts/search.py.
# Workspace adaptation: caller-supplied projections, scoped corpus statistics,
# per-call SQLite connections, source hashes, external cache, no semantic layer.
"""Small SQLite BM25 index over Reader projections, never source directories."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import math
from pathlib import Path
import re
import sqlite3
import unicodedata

TITLE_WEIGHT = 3
K1, B = 1.5, 0.75
_ASCII_RE = re.compile(r"[a-z0-9]+")


def _is_cjk(ch):
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


def tokenize(text):
    """Upstream NFKC ASCII words and adjacent CJK bigrams."""
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = list(_ASCII_RE.findall(text))
    run = []
    for ch in text:
        if _is_cjk(ch):
            run.append(ch)
        else:
            if len(run) == 1:
                tokens.append(run[0])
            elif len(run) > 1:
                tokens.extend(run[i] + run[i + 1] for i in range(len(run) - 1))
            run = []
    if len(run) == 1:
        tokens.append(run[0])
    elif len(run) > 1:
        tokens.extend(run[i] + run[i + 1] for i in range(len(run) - 1))
    return tokens


def _snippet(text: str, query: str, width: int = 160) -> str:
    flat = " ".join(text.split())
    folded = flat.casefold()
    positions = [folded.find(term.casefold()) for term in [query, *tokenize(query)]]
    found = [position for position in positions if position >= 0]
    start = max(0, min(found) - width // 3) if found else 0
    end = start + width
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


def rank_documents(query: str, documents: list[dict], limit: int = 20) -> list[dict]:
    """Rank already-authorized live Reader projections with the workspace BM25 rules.

    This pure path is for request-scoped private readers that must not create a
    persistent SQLite projection. The regular Workspace still uses SearchIndex.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("Search limit must be between 1 and 500")
    if not isinstance(query, str) or len(query) > 2000:
        raise ValueError("Search query must be at most 2000 characters")
    terms = sorted(set(tokenize(query)))
    if len(terms) > 128:
        raise ValueError("Search query has too many terms")
    if not documents or not terms:
        return []
    prepared = []
    for position, document in enumerate(documents):
        if not isinstance(document, dict) or any(not isinstance(document.get(key), str)
                for key in ("vault_id", "path", "title", "format", "source_hash", "search_text")):
            raise ValueError("Invalid live search projection")
        counts = Counter(tokenize(document["search_text"]))
        counts.update({token: count * TITLE_WEIGHT for token, count in Counter(tokenize(document["title"])).items()})
        prepared.append((position, document, counts, sum(counts.values())))
    total_length = sum(item[3] for item in prepared)
    if not total_length:
        return []
    average_length = total_length / len(prepared)
    document_frequency = {term: sum(1 for _, _, counts, _ in prepared if counts.get(term, 0)) for term in terms}
    scored = []
    minimum_matches = max(1, len(terms) // 2)
    for position, document, counts, length in prepared:
        score = 0.0
        matched = 0
        for term in terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            frequency_in_corpus = document_frequency[term]
            inverse = math.log(1 + (len(prepared) - frequency_in_corpus + 0.5) / (frequency_in_corpus + 0.5))
            norm = frequency * (K1 + 1) / (frequency + K1 * (1 - B + B * length / average_length))
            score += inverse * norm
            matched += 1
        if matched >= minimum_matches:
            scored.append((position, document, score))
    scored.sort(key=lambda item: (-item[2], item[0]))
    results = []
    for _, document, score in scored[:limit]:
        item = {key: document.get(key) for key in ("vault_id", "path", "title", "type_key", "format", "source_hash")}
        item.update(score=score, snippet=_snippet(document["search_text"], query))
        results.append(item)
    return results


class SearchIndex:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS docs (
                    id INTEGER PRIMARY KEY, vault_id TEXT NOT NULL, path TEXT NOT NULL,
                    title TEXT NOT NULL, type_key TEXT, format TEXT NOT NULL,
                    source_hash TEXT NOT NULL, search_text TEXT NOT NULL,
                    length INTEGER NOT NULL, UNIQUE(vault_id, path)
                );
                CREATE INDEX IF NOT EXISTS idx_docs_vault ON docs(vault_id);
                CREATE TABLE IF NOT EXISTS postings (
                    term TEXT NOT NULL, doc_id INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
                    tf INTEGER NOT NULL, PRIMARY KEY(term, doc_id)
                ) WITHOUT ROWID;
                CREATE INDEX IF NOT EXISTS idx_postings_doc ON postings(doc_id);
            """)

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def refresh(self, vault_id: str, documents: list[dict]) -> dict:
        if not isinstance(vault_id, str) or not vault_id:
            raise ValueError("Vault ID is required")
        fields = ("path", "title", "format", "source_hash", "search_text")
        prepared = []
        seen = set()
        for document in documents:
            if not isinstance(document, dict) or any(not isinstance(document.get(key), str) for key in fields):
                raise ValueError("Invalid Reader document projection")
            if not document["path"] or document["path"] in seen:
                raise ValueError("Duplicate or empty document path")
            if document.get("type_key") is not None and not isinstance(document["type_key"], str):
                raise ValueError("Document type_key must be text or null")
            seen.add(document["path"])
            prepared.append(document)
        changed = 0
        with self._connection() as conn:
            # Serialize writers before reading the old snapshot, including two
            # refresh calls for the same Vault from different request threads.
            conn.execute("BEGIN IMMEDIATE")
            known = {row["path"]: row for row in conn.execute("SELECT * FROM docs WHERE vault_id=?", (vault_id,))}
            for document in prepared:
                old = known.get(document["path"])
                if old is not None and all(old[key] == document.get(key) for key in (*fields, "type_key")):
                    continue
                counts = Counter(tokenize(document["search_text"]))
                counts.update({token: count * TITLE_WEIGHT for token, count in Counter(tokenize(document["title"])).items()})
                values = (vault_id, document["path"], document["title"], document.get("type_key"), document["format"],
                          document["source_hash"], document["search_text"], sum(counts.values()))
                conn.execute("""INSERT INTO docs(vault_id,path,title,type_key,format,source_hash,search_text,length)
                    VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(vault_id,path) DO UPDATE SET
                    title=excluded.title,type_key=excluded.type_key,format=excluded.format,
                    source_hash=excluded.source_hash,search_text=excluded.search_text,length=excluded.length""", values)
                doc_id = conn.execute("SELECT id FROM docs WHERE vault_id=? AND path=?", (vault_id, document["path"])).fetchone()[0]
                conn.execute("DELETE FROM postings WHERE doc_id=?", (doc_id,))
                conn.executemany("INSERT INTO postings(term,doc_id,tf) VALUES(?,?,?)", ((term, doc_id, count) for term, count in counts.items()))
                changed += 1
            removed = set(known) - seen
            conn.executemany("DELETE FROM docs WHERE vault_id=? AND path=?", ((vault_id, path) for path in removed))
        return {"indexed": len(prepared), "changed": changed, "removed": len(removed)}

    def search(self, query: str, vault_ids: list[str], limit: int = 20) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("Search limit must be between 1 and 100")
        if not isinstance(query, str) or len(query) > 2000:
            raise ValueError("Search query must be at most 2000 characters")
        if not isinstance(vault_ids, list) or len(vault_ids) > 1000 or any(not isinstance(item, str) for item in vault_ids):
            raise ValueError("Invalid Vault search scope")
        scope = sorted(set(vault_ids))
        terms = sorted(set(tokenize(query)))
        if len(terms) > 128:
            raise ValueError("Search query has too many terms")
        if not scope or not terms:
            return []
        placeholders = ",".join("?" for _ in scope)
        with self._connection() as conn:
            # One read transaction gives corpus statistics and postings the same
            # snapshot while another request refreshes the index.
            conn.execute("BEGIN")
            n_docs, total_len = conn.execute(f"SELECT COUNT(*), COALESCE(SUM(length),0) FROM docs WHERE vault_id IN ({placeholders})", scope).fetchone()
            if not n_docs or not total_len:
                return []
            avg_len = total_len / n_docs
            scores: dict[int, float] = {}
            matched_terms: Counter = Counter()
            for term in terms:
                rows = conn.execute(f"""SELECT p.doc_id,p.tf,d.length FROM postings p JOIN docs d ON d.id=p.doc_id
                    WHERE p.term=? AND d.vault_id IN ({placeholders})""", [term, *scope]).fetchall()
                if not rows:
                    continue
                idf = math.log(1 + (n_docs - len(rows) + 0.5) / (len(rows) + 0.5))
                for doc_id, tf, length in rows:
                    norm = tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / avg_len))
                    scores[doc_id] = scores.get(doc_id, 0.0) + idf * norm
                    matched_terms[doc_id] += 1
            need = max(1, len(terms) // 2)
            ranked = sorted(((doc_id, score) for doc_id, score in scores.items() if matched_terms[doc_id] >= need), key=lambda pair: (-pair[1], pair[0]))[:limit]
            results = []
            for doc_id, score in ranked:
                row = conn.execute("SELECT * FROM docs WHERE id=?", (doc_id,)).fetchone()
                item = {key: row[key] for key in ("vault_id", "path", "title", "type_key", "format", "source_hash")}
                item.update(score=score, snippet=_snippet(row["search_text"], query))
                results.append(item)
            return results

    def clear(self, vault_id: str) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM docs WHERE vault_id=?", (vault_id,))
