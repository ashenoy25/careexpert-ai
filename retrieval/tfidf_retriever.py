# CareExpert AI - TF-IDF Retrieval Module
# Handles document loading, chunking, and TF-IDF-based retrieval

import streamlit as st
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from config.sources import get_source_display


@st.cache_resource(show_spinner="Loading CareExpert AI knowledge base...")
def build_retriever():
    """Load documents, chunk them, build TF-IDF index."""
    kb_path = Path(__file__).parent.parent / "knowledge_base"
    if not kb_path.exists():
        return None, None, None, None, {}

    chunks = []
    chunk_sources = []
    chunk_source_keys = []
    kb_stats = {"total_chars": 0, "total_lines": 0, "files": {}}

    for md_file in sorted(kb_path.glob("*.md")):
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        file_key = md_file.stem
        source_info = get_source_display(file_key)
        doc_name = f"{source_info['name']} ({source_info['org']})"

        # Track stats
        file_lines = content.count("\n") + 1
        file_chars = len(content)
        kb_stats["total_chars"] += file_chars
        kb_stats["total_lines"] += file_lines
        kb_stats["files"][file_key] = {"lines": file_lines, "chars": file_chars}

        sections = []
        current_section = ""
        for line in content.split("\n"):
            if line.startswith("## ") and current_section.strip():
                sections.append(current_section)
                current_section = line + "\n"
            else:
                current_section += line + "\n"
        if current_section.strip():
            sections.append(current_section)

        for section in sections:
            words = section.split()
            if len(words) <= 800:
                if len(words) > 30:
                    chunks.append(section.strip())
                    chunk_sources.append(doc_name)
                    chunk_source_keys.append(file_key)
            else:
                for i in range(0, len(words), 600):
                    chunk_words = words[i:i+800]
                    if len(chunk_words) > 30:
                        chunks.append(" ".join(chunk_words))
                        chunk_sources.append(doc_name)
                        chunk_source_keys.append(file_key)

    vectorizer = TfidfVectorizer(
        max_features=10000, stop_words="english",
        ngram_range=(1, 2), min_df=1, max_df=0.95,
    )
    tfidf_matrix = vectorizer.fit_transform(chunks)

    return chunks, chunk_sources, chunk_source_keys, (vectorizer, tfidf_matrix), kb_stats


def retrieve_relevant_chunks(query, chunks, chunk_sources, chunk_source_keys, retriever_data, top_k=8):
    """Find most relevant chunks using TF-IDF cosine similarity."""
    vectorizer, tfidf_matrix = retriever_data
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if similarities[idx] > 0.05:
            source_key = chunk_source_keys[idx]
            results.append({
                "text": chunks[idx],
                "source": chunk_sources[idx],
                "source_key": source_key,
                "source_info": get_source_display(source_key),
                "score": float(similarities[idx]),
            })
    return results
