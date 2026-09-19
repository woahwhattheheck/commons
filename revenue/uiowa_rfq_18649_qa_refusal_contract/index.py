"""Deterministic keyword index over the evidence packet. Stdlib only.

Why this is not a retrieval system
----------------------------------
The temptation in a Q&A kit is: index the evidence, retrieve the nearest three
chunks for any question, hand them to a model, print the paragraph. That
pipeline can never say "I don't know", because top-k retrieval is never empty.
Ask it where the University ranks against its peers and it will return the
three most peer-adjacent sentences in the corpus and write a confident answer
on top of them. The evidence did not contain the answer; the shape of the
system guaranteed one anyway.

So this index does not produce answers. It *routes* questions to answer records
that were authored against specific evidence, and it is allowed to route to
nothing. Two gates, both of which must pass:

  score     a tf-idf cosine-ish similarity, guarding against noise
  coverage  the fraction of the question's own distinctive terms that the
            candidate actually contains

Coverage is the load-bearing one. Score alone is a relative measure -- the best
of a bad field still wins. Coverage is absolute: if the question asks about
"peer percentile ranking" and the candidate record contains none of
{peer, percentile, rank}, it does not matter that it outscored everything else
in the corpus. It is not about the same subject, and the honest output is
nothing.

No stemming beyond plural stripping, no synonyms, no embeddings. Every routing
decision is inspectable by hand, and `explain()` prints the arithmetic.
"""

import math
import re

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_\-]*")

# Deliberately short. An aggressive stopword list silently deletes the
# distinctive term of a question ("no", "not", "never" all matter here) and
# then coverage passes for the wrong reason.
STOPWORDS = frozenset("""
a an the and or but of for to in on at by with from as is are was were be been
being do does did doing have has had having this that these those it its we us
our you your they them their i me my he she his her what which who whom how
why when where can could should would will shall may might must if then than
so such about into over under again further more most other some any each
""".split())


def tokenize(text):
    """Lowercase word tokens with naive plural stripping."""
    out = []
    for raw in _TOKEN.findall((text or "").lower()):
        if raw in STOPWORDS:
            continue
        # Naive singularisation. "process"/"access" must not become "proces".
        if len(raw) > 3 and raw.endswith("s") and not raw.endswith(("ss", "us", "is")):
            raw = raw[:-1]
        out.append(raw)
    return out


def content_terms(text):
    """The distinctive terms of a question, deduplicated, order preserved."""
    seen = []
    for tok in tokenize(text):
        if tok not in seen:
            seen.append(tok)
    return seen


class Document:
    """One indexable thing: an answer record, an evidence item, a boundary."""

    def __init__(self, doc_id, kind, text, payload=None):
        self.doc_id = doc_id
        self.kind = kind
        self.text = text
        self.payload = payload if payload is not None else {}
        self.tokens = tokenize(text)
        self.term_set = frozenset(self.tokens)
        self.tf = {}
        for tok in self.tokens:
            self.tf[tok] = self.tf.get(tok, 0) + 1


class Match:
    def __init__(self, doc, score, coverage, matched, missing):
        self.doc = doc
        self.score = score
        self.coverage = coverage
        self.matched = matched
        self.missing = missing

    def as_dict(self):
        return {
            "id": self.doc.doc_id,
            "kind": self.doc.kind,
            "score": round(self.score, 4),
            "coverage": round(self.coverage, 4),
            "matched_terms": list(self.matched),
            "question_terms_not_in_record": list(self.missing),
        }


class KeywordIndex:
    """tf-idf over a small corpus. Deterministic, no randomness, no clock."""

    def __init__(self):
        self.docs = []
        self._by_id = {}
        self._df = {}
        self._idf = {}

    def add(self, doc):
        if doc.doc_id in self._by_id:
            raise ValueError("duplicate document id: %s" % doc.doc_id)
        self.docs.append(doc)
        self._by_id[doc.doc_id] = doc

    def get(self, doc_id):
        return self._by_id.get(doc_id)

    def build(self):
        self._df = {}
        for doc in self.docs:
            for term in doc.term_set:
                self._df[term] = self._df.get(term, 0) + 1
        n = max(len(self.docs), 1)
        self._idf = {}
        for term, df in self._df.items():
            # Smoothed idf; a term in every document contributes ~0.
            self._idf[term] = math.log((n + 1.0) / (df + 1.0)) + 1.0
        return self

    def idf(self, term):
        # An unseen term is maximally distinctive -- it also means no document
        # covers it, which is exactly the signal we want to keep.
        n = max(len(self.docs), 1)
        return self._idf.get(term, math.log((n + 1.0) / 1.0) + 1.0)

    def _weights(self, tf):
        w = {}
        for term, count in tf.items():
            w[term] = (1.0 + math.log(count)) * self.idf(term)
        norm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        return w, norm

    def search(self, query, kinds=None, limit=5):
        """Ranked matches, each carrying its own coverage arithmetic."""
        q_terms = content_terms(query)
        if not q_terms:
            return []
        q_tf = {}
        for tok in tokenize(query):
            q_tf[tok] = q_tf.get(tok, 0) + 1
        qw, qnorm = self._weights(q_tf)

        results = []
        for doc in self.docs:
            if kinds and doc.kind not in kinds:
                continue
            dw, dnorm = self._weights(doc.tf)
            dot = 0.0
            for term, weight in qw.items():
                if term in dw:
                    dot += weight * dw[term]
            score = dot / (qnorm * dnorm)

            matched = [t for t in q_terms if t in doc.term_set]
            missing = [t for t in q_terms if t not in doc.term_set]
            # Coverage is idf-weighted: missing a rare, distinctive term
            # ("percentile") costs far more than missing a common one
            # ("practice"). An unweighted fraction lets a candidate pass by
            # matching filler.
            total_w = sum(self.idf(t) for t in q_terms) or 1.0
            cov = sum(self.idf(t) for t in matched) / total_w

            if score > 0.0:
                results.append(Match(doc, score, cov, matched, missing))

        results.sort(key=lambda m: (-m.score, m.doc.doc_id))
        return results[:limit]

    def explain(self, query, limit=5):
        """Human-readable routing arithmetic. Used by the CLI's audit path."""
        lines = ["question terms: %s" % ", ".join(content_terms(query))]
        matches = self.search(query, limit=limit)
        if not matches:
            lines.append("  (no document shares a single content term)")
        for m in matches:
            lines.append(
                "  %-28s score=%.4f coverage=%.4f  matched=[%s] missing=[%s]"
                % (m.doc.doc_id, m.score, m.coverage,
                   " ".join(m.matched), " ".join(m.missing)))
        return "\n".join(lines)
