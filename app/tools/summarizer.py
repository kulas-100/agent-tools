"""
Summarizer Tool — Extractive text summarization using TF-IDF-inspired sentence scoring.
No external LLM calls — runs entirely on-server at zero cost.
"""
import re
from typing import List, Tuple
from collections import Counter
from app.models import SummarizeRequest, SummarizeResponse

# Common English stopwords to exclude from scoring
STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "not",
    "no", "so", "as", "if", "then", "than", "there", "their", "they",
    "its", "our", "my", "your", "his", "her", "about", "which", "who",
    "whom", "what", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "up", "down", "also", "just", "only", "very", "too", "even",
    "now", "here", "any", "one", "two", "three", "get", "got", "like",
    "use", "used", "said", "say", "make", "made", "new", "well", "back",
    "over", "still", "while", "however", "although", "because", "since",
})


def _tokenize_words(text: str) -> List[str]:
    """Extract meaningful words from text."""
    return re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences and filter empty/short ones."""
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 20]


async def summarize_text(request: SummarizeRequest) -> SummarizeResponse:
    """Produce an extractive summary via ranked sentence selection."""
    text = request.text.strip()
    sentences = _split_sentences(text)

    if not sentences:
        return SummarizeResponse(
            original_length=len(text),
            summary=text,
            summary_length=len(text),
            compression_ratio=1.0,
        )

    # If already short enough, return as-is
    if len(sentences) <= request.num_sentences:
        return SummarizeResponse(
            original_length=len(text),
            summary=" ".join(sentences),
            summary_length=len(" ".join(sentences)),
            compression_ratio=1.0,
        )

    # Build word frequency table (excluding stopwords)
    all_words = _tokenize_words(text)
    freq = Counter(w for w in all_words if w not in STOPWORDS)

    # Normalize frequencies to [0, 1]
    max_freq = freq.most_common(1)[0][1] if freq else 1
    norm_freq = {w: c / max_freq for w, c in freq.items()}

    # Score each sentence
    scored: List[Tuple[float, int]] = []
    for i, sentence in enumerate(sentences):
        words = _tokenize_words(sentence)
        content_words = [w for w in words if w not in STOPWORDS]
        if not content_words:
            scored.append((0.0, i))
            continue

        score = sum(norm_freq.get(w, 0) for w in content_words) / len(content_words)

        # Position bonus: first and last sentences are often most important
        if i == 0:
            score *= 1.6
        elif i == len(sentences) - 1:
            score *= 1.2
        elif i < len(sentences) // 4:
            score *= 1.1

        scored.append((score, i))

    # Grab top-N, re-sorted by original order
    top_n = request.num_sentences
    top_indices = sorted(
        sorted(scored, key=lambda x: x[0], reverse=True)[:top_n],
        key=lambda x: x[1],
    )

    summary = " ".join(sentences[i] for _, i in top_indices)

    return SummarizeResponse(
        original_length=len(text),
        summary=summary,
        summary_length=len(summary),
        compression_ratio=round(len(summary) / len(text), 3),
    )
