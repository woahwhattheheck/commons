from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

STAGES = ("anticipate", "plan", "decide", "monitor", "execute")
DOMAINS = ("care", "food", "home", "schedule", "social_admin")

_STAGE_EXAMPLES = {
    "anticipate": [
        "remember the school form is due next week",
        "we need to notice when the prescription refill is getting low",
        "check whether the kids need new shoes before term starts",
        "keep an eye on when the permission slip will be needed",
        "anticipate supplies before we run out",
    ],
    "plan": [
        "compare summer camp options and make a plan",
        "organize meals for the week and make the grocery list",
        "figure out pickup coverage for thursday",
        "research three repair options and schedule a window",
        "plan the birthday logistics and guest list",
    ],
    "decide": [
        "choose which after school option we should use",
        "decide between the two appointment times",
        "pick the repair quote we are going with",
        "select which groceries to substitute",
        "approve the final family calendar plan",
    ],
    "monitor": [
        "follow up because the school has not confirmed",
        "track whether the form was returned",
        "check that the repair person actually arrived",
        "remind everyone before the deadline",
        "monitor the waitlist and send another follow up",
    ],
    "execute": [
        "buy the groceries on the list",
        "drive to the appointment",
        "submit the completed form",
        "pick up the package",
        "clean the kitchen after dinner",
    ],
}

_DOMAIN_EXAMPLES = {
    "care": [
        "school permission form child pickup daycare appointment caregiver",
        "after school camp pediatric paperwork family care",
        "childcare elder care dependent support school nurse",
    ],
    "food": [
        "meal plan groceries pantry dinner lunch breakfast shopping",
        "grocery list food allergy-safe substitution ingredients",
        "cook dinner order groceries meal prep",
    ],
    "home": [
        "repair plumber laundry cleaning supplies home maintenance",
        "replace lightbulb call contractor fix appliance household",
        "trash kitchen clean package home chore",
    ],
    "schedule": [
        "calendar appointment pickup meeting deadline schedule time",
        "book appointment coordinate availability reschedule commute",
        "calendar invite timing pickup coverage",
    ],
    "social_admin": [
        "birthday guest list gift thank you card permission form email",
        "renew membership fill paperwork family admin invitation",
        "school email forms social plans travel documents",
    ],
}


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
    scores: dict[str, float]


class NaiveBayesTextClassifier:
    """Tiny deterministic multinomial NB classifier for the offline prototype.

    It is intentionally small and inspectable. Production can replace this with
    an on-device or hosted model behind the same label contract.
    """

    def __init__(self, examples: dict[str, Iterable[str]]) -> None:
        if not examples:
            raise ValueError("examples must not be empty")
        self.labels = tuple(sorted(examples))
        self.doc_counts: Counter[str] = Counter()
        self.word_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.total_words: Counter[str] = Counter()
        self.vocab: set[str] = set()
        for label in self.labels:
            docs = list(examples[label])
            if not docs:
                raise ValueError(f"label {label} has no examples")
            for doc in docs:
                self.doc_counts[label] += 1
                tokens = tokenize(doc)
                self.word_counts[label].update(tokens)
                self.total_words[label] += len(tokens)
                self.vocab.update(tokens)
        self.total_docs = sum(self.doc_counts.values())

    def predict(self, text: str) -> Prediction:
        tokens = tokenize(text)
        vocab_size = max(1, len(self.vocab))
        log_scores: dict[str, float] = {}
        for label in self.labels:
            prior = self.doc_counts[label] / self.total_docs
            score = math.log(prior)
            denom = self.total_words[label] + vocab_size
            for token in tokens:
                score += math.log((self.word_counts[label][token] + 1) / denom)
            log_scores[label] = score
        best = max(self.labels, key=lambda label: (log_scores[label], label))
        max_log = max(log_scores.values())
        exps = {label: math.exp(value - max_log) for label, value in log_scores.items()}
        total = sum(exps.values())
        probs = {label: exps[label] / total for label in self.labels}
        return Prediction(best, probs[best], probs)


STAGE_MODEL = NaiveBayesTextClassifier(_STAGE_EXAMPLES)
DOMAIN_MODEL = NaiveBayesTextClassifier(_DOMAIN_EXAMPLES)
