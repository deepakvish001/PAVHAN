"""PAVHAN search.

A craft marketplace has a specific search problem: the buyer types "banarasi
saree", the artisan wrote "बनारसी साड़ी", and somebody else calls the same
thing a "sari". So the index normalises Devanagari and Roman spellings into one
synonym space before it scores anything.

Scoring is BM25 over a weighted field concatenation, plus a fuzzy pass for
typos ("pashmena"), plus facet counts so the UI can build filters from live
data rather than a hardcoded list.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Each group is one concept; any member maps to the group's canonical head.
SYNONYM_GROUPS: list[list[str]] = [
    ["saree", "sari", "sadi", "साड़ी", "शाड़ी"],
    ["dupatta", "odhni", "chunni", "दुपट्टा", "चुन्नी"],
    ["shawl", "shaal", "stole", "wrap", "शॉल"],
    ["silk", "resham", "रेशम", "सिल्क"],
    ["cotton", "sooti", "suti", "सूती", "कपास"],
    ["pottery", "ceramic", "mitti", "clay", "मिट्टी", "बर्तन"],
    ["painting", "art", "chitra", "artwork", "चित्र", "पेंटिंग", "कला"],
    ["jewellery", "jewelry", "gehna", "ornament", "गहना", "आभूषण"],
    ["toy", "khilona", "खिलौना"],
    ["basket", "tokri", "टोकरी"],
    ["bag", "thaila", "jhola", "tote", "थैला"],
    ["lamp", "diya", "deepak", "दीया", "दीपक"],
    ["handmade", "handcrafted", "hastnirmit", "haath", "हस्तनिर्मित", "हाथ"],
    ["banarasi", "banaras", "varanasi", "बनारसी", "वाराणसी"],
    ["pashmina", "cashmere", "पश्मीना"],
    ["blue", "neela", "नीला"],
    ["red", "laal", "lal", "लाल"],
    ["green", "hara", "हरा"],
    ["gold", "golden", "sunehra", "सुनहरा"],
    ["gift", "gifting", "present", "उपहार"],
    ["wedding", "bridal", "shaadi", "शादी"],
    ["eco", "sustainable", "organic", "natural", "प्राकृतिक"],
    ["vase", "guldasta", "flowerpot", "गुलदस्ता"],
    ["embroidery", "kadhai", "कढ़ाई"],
]

SYNONYM_MAP: dict[str, str] = {}
for group in SYNONYM_GROUPS:
    head = group[0]
    for word in group:
        SYNONYM_MAP[word] = head

STOPWORDS = {
    "a", "an", "the", "of", "for", "with", "and", "or", "in", "on", "to", "is",
    "hai", "ka", "ki", "ke", "se", "me", "mein", "yeh", "ye", "aur", "ek",
    "है", "का", "की", "के", "से", "में", "और", "एक",
}

TOKEN_RE = re.compile(r"[a-z0-9ऀ-ॿ]+")

# Field weights — a title hit matters far more than a description hit.
FIELD_WEIGHTS = {
    "title": 4.0, "craft_type": 3.0, "category": 2.5, "material": 2.5,
    "region": 2.5, "colour": 2.0, "tags": 2.0, "keywords": 1.8,
    "technique": 1.5, "short_description": 1.2, "detailed_description": 0.7,
    "story": 0.5,
}

K1, B = 1.5, 0.75


def normalise(token: str) -> str:
    token = token.lower().strip()
    return SYNONYM_MAP.get(token, token)


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall((text or "").lower())
    return [normalise(t) for t in tokens if t not in STOPWORDS and len(t) > 1]


@dataclass
class SearchHit:
    product_id: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    highlight: str = ""


class SearchIndex:
    """In-memory BM25 index, rebuilt whenever the catalogue changes."""

    def __init__(self) -> None:
        self.doc_tokens: dict[str, list[str]] = {}
        self.doc_weights: dict[str, dict[str, float]] = {}
        self.df: dict[str, int] = defaultdict(int)
        self.doc_len: dict[str, float] = {}
        self.avg_len: float = 1.0
        self.vocabulary: set[str] = set()
        self.docs: dict[str, object] = {}

    def build(self, products: list) -> None:
        self.__init__()
        for p in products:
            weights: dict[str, float] = defaultdict(float)
            all_tokens: list[str] = []
            for fieldname, weight in FIELD_WEIGHTS.items():
                raw = getattr(p, fieldname, "") or ""
                if isinstance(raw, list):
                    raw = " ".join(str(x) for x in raw)
                tokens = tokenize(str(raw))
                all_tokens.extend(tokens)
                for t in tokens:
                    weights[t] += weight
            self.doc_tokens[p.id] = all_tokens
            self.doc_weights[p.id] = dict(weights)
            self.doc_len[p.id] = sum(weights.values()) or 1.0
            self.docs[p.id] = p
            for t in set(all_tokens):
                self.df[t] += 1
                self.vocabulary.add(t)
        if self.doc_len:
            self.avg_len = sum(self.doc_len.values()) / len(self.doc_len)

    # -- query helpers ------------------------------------------------------
    def _fuzzy_expand(self, term: str) -> list[tuple[str, float]]:
        """Typo tolerance: 'pashmena' -> 'pashmina' at a 0.82 confidence."""
        if term in self.vocabulary or len(term) < 4:
            return []
        out = []
        for word in self.vocabulary:
            if abs(len(word) - len(term)) > 3:
                continue
            ratio = SequenceMatcher(None, term, word).ratio()
            if ratio >= 0.8:
                out.append((word, ratio))
        return sorted(out, key=lambda x: -x[1])[:2]

    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        prefix = normalise(prefix)
        if not prefix:
            return []
        starts = sorted(
            (w for w in self.vocabulary if w.startswith(prefix)),
            key=lambda w: (-self.df.get(w, 0), w),
        )
        return starts[:limit]

    def did_you_mean(self, query: str) -> str | None:
        terms = tokenize(query)
        if not terms:
            return None
        fixed, changed = [], False
        for t in terms:
            if t in self.vocabulary:
                fixed.append(t)
                continue
            alt = self._fuzzy_expand(t)
            if alt:
                fixed.append(alt[0][0])
                changed = True
            else:
                fixed.append(t)
        return " ".join(fixed) if changed else None

    def search(self, query: str) -> list[SearchHit]:
        terms = tokenize(query)
        if not terms:
            return []
        n = max(len(self.doc_tokens), 1)
        expanded: list[tuple[str, float]] = [(t, 1.0) for t in terms]
        for t in terms:
            expanded.extend((alt, ratio * 0.75) for alt, ratio in self._fuzzy_expand(t))

        scores: dict[str, float] = defaultdict(float)
        matched: dict[str, set] = defaultdict(set)
        for term, boost in expanded:
            df = self.df.get(term, 0)
            if not df:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for doc_id, weights in self.doc_weights.items():
                tf = weights.get(term, 0.0)
                if not tf:
                    continue
                norm = 1 - B + B * (self.doc_len[doc_id] / self.avg_len)
                score = idf * (tf * (K1 + 1)) / (tf + K1 * norm)
                scores[doc_id] += score * boost
                matched[doc_id].add(term)

        # A document matching every query term should always outrank one that
        # matched a single common term many times.
        hits = []
        for doc_id, score in scores.items():
            coverage = len(matched[doc_id]) / len(terms)
            hits.append(SearchHit(doc_id, round(score * (0.55 + 0.45 * coverage), 4),
                                  sorted(matched[doc_id])))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits


def apply_filters(products: list, filters: dict) -> list:
    out = []
    for p in products:
        if filters.get("category") and p.category != filters["category"]:
            continue
        if filters.get("craft_type") and p.craft_type != filters["craft_type"]:
            continue
        if filters.get("material") and p.material != filters["material"]:
            continue
        if filters.get("region") and p.region != filters["region"]:
            continue
        if filters.get("colour") and filters["colour"].lower() not in (p.colour or "").lower():
            continue
        if filters.get("min_price") is not None and p.price < filters["min_price"]:
            continue
        if filters.get("max_price") is not None and p.price > filters["max_price"]:
            continue
        if filters.get("gi_only") and not p.gi_tagged:
            continue
        if filters.get("max_lead_time") is not None and p.lead_time_days > filters["max_lead_time"]:
            continue
        if filters.get("min_quality") is not None and p.quality_score < filters["min_quality"]:
            continue
        out.append(p)
    return out


def build_facets(products: list) -> dict:
    facets: dict[str, dict[str, int]] = {
        "category": defaultdict(int), "craft_type": defaultdict(int),
        "material": defaultdict(int), "region": defaultdict(int),
        "colour": defaultdict(int),
    }
    prices = []
    for p in products:
        for key in facets:
            value = getattr(p, key, "") or ""
            if value:
                facets[key][value] += 1
        if p.price:
            prices.append(p.price)
    out: dict = {
        key: sorted(
            [{"value": v, "count": c} for v, c in counts.items()],
            key=lambda x: (-x["count"], x["value"]),
        )[:14]
        for key, counts in facets.items()
    }
    out["price"] = {
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "buckets": _price_buckets(prices),
    }
    return out


def _price_buckets(prices: list[float]) -> list[dict]:
    if not prices:
        return []
    bands = [(0, 500), (500, 1500), (1500, 4000), (4000, 10000), (10000, 10**9)]
    labels = ["Under Rs.500", "Rs.500-1,500", "Rs.1,500-4,000",
              "Rs.4,000-10,000", "Above Rs.10,000"]
    return [
        {"label": label, "min": lo, "max": None if hi > 10**8 else hi,
         "count": sum(1 for p in prices if lo <= p < hi)}
        for (lo, hi), label in zip(bands, labels)
    ]


SORTS = {
    "relevance": None,
    "price_asc": lambda p: p.price,
    "price_desc": lambda p: -p.price,
    "newest": lambda p: -p.created_at.timestamp() if p.created_at else 0,
    "quality": lambda p: -p.quality_score,
    "popular": lambda p: -(p.views * 2 + p.rating * 20),
}

index = SearchIndex()
