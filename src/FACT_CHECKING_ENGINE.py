from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# RDF property URIs used in the input files.
# Each fact is represented as an rdf:Statement with subject, predicate, and object.
RDF_SUBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject"
RDF_PREDICATE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate"
RDF_OBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#object"

# Property URI required by the GERBIL fact-checking task.
TRUTH_VALUE = "http://swc2017.aksw.org/hasTruthValue"

# GERBIL expects predicted truth values to be written as xsd:double.
XSD_DOUBLE = "http://www.w3.org/2001/XMLSchema#double"

# Regular expressions for reading simple N-Triples/Turtle-style lines.
TRIPLE_RE = re.compile(r'^\s*<([^>]+)>\s+<([^>]+)>\s+(.+?)\s*\.\s*$')
URI_RE = re.compile(r'^<([^>]+)>$')
LITERAL_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"(?:\^\^<([^>]+)>)?$')

# Stores one extracted RDF fact.
@dataclass(frozen=True)
class Fact:
    fact_uri: str
    subject: str
    predicate: str
    object: str
    truth: float | None = None

# Removes RDF URI/literal wrappers from an object value.
def parse_object(raw: str) -> str:
    uri_match = URI_RE.match(raw)
    if uri_match:
        return uri_match.group(1)
    literal_match = LITERAL_RE.match(raw)
    if literal_match:
        return literal_match.group(1)
    return raw

# Reads a statement file and converts it into Fact objects.
def parse_statement_file(path: Path) -> list[Fact]:
    statements: dict[str, dict[str, object]] = defaultdict(dict)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = TRIPLE_RE.match(line)
            if not match:
                raise ValueError(f"Could not parse line {line_number} in {path}: {line}")
            statement_uri, predicate, raw_object = match.groups()
            obj = parse_object(raw_object)
            if predicate == RDF_SUBJECT:
                statements[statement_uri]["subject"] = obj
            elif predicate == RDF_PREDICATE:
                statements[statement_uri]["predicate"] = obj
            elif predicate == RDF_OBJECT:
                statements[statement_uri]["object"] = obj
            elif predicate == TRUTH_VALUE:
                statements[statement_uri]["truth"] = float(obj)
    facts: list[Fact] = []
    for fact_uri, fields in statements.items():
        missing = {"subject", "predicate", "object"} - fields.keys()
        if missing:
            raise ValueError(f"Statement {fact_uri} is missing required fields: {sorted(missing)}")
        facts.append(Fact(fact_uri, str(fields["subject"]), str(fields["predicate"]), str(fields["object"]), float(fields["truth"]) if "truth" in fields else None))
    return facts

# Gets the readable final part of a URI.
def uri_tail(uri: str) -> str:
    return uri.rsplit("/", 1)[-1].rsplit("#", 1)[-1].replace("_", " ").replace(",", " ").lower()

# Splits a URI name into simple text tokens.
def token_set(uri: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", uri_tail(uri)) if len(token) > 2}

# Calculates a smoothed probability to avoid overconfident scores.
def beta_mean(successes: float, total: float, prior: float = 0.5, strength: float = 4.0) -> float:
    return (successes + prior * strength) / (total + strength)

# Converts a probability into log-odds.
def logit(value: float) -> float:
    value = min(max(value, 1e-6), 1.0 - 1e-6)
    return math.log(value / (1.0 - value))

# Converts log-odds back into a probability.
def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))

# Learns simple statistical patterns from training facts.
class FactScorer:
    def __init__(self) -> None:
        self.global_rate = 0.5
        self.predicate_counts: Counter[str] = Counter()
        self.predicate_true: Counter[str] = Counter()
        self.subject_counts: Counter[str] = Counter()
        self.subject_true: Counter[str] = Counter()
        self.object_counts: Counter[str] = Counter()
        self.object_true: Counter[str] = Counter()
        self.subject_predicate_counts: Counter[tuple[str, str]] = Counter()
        self.subject_predicate_true: Counter[tuple[str, str]] = Counter()
        self.predicate_object_counts: Counter[tuple[str, str]] = Counter()
        self.predicate_object_true: Counter[tuple[str, str]] = Counter()
        self.triple_counts: Counter[tuple[str, str, str]] = Counter()
        self.triple_true: Counter[tuple[str, str, str]] = Counter()
        self.true_objects_by_subject_predicate: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.functional_predicates: set[str] = set()

    # Learns truth-rate statistics from labeled facts.
    def fit(self, facts: Iterable[Fact]) -> None:
        labeled = [fact for fact in facts if fact.truth is not None]
        if not labeled:
            raise ValueError("Training data must contain hasTruthValue labels.")
        total_true = sum(float(fact.truth or 0.0) for fact in labeled)
        self.global_rate = beta_mean(total_true, len(labeled))
        true_object_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
        for fact in labeled:
            y = 1.0 if (fact.truth or 0.0) >= 0.5 else 0.0
            sp = (fact.subject, fact.predicate)
            po = (fact.predicate, fact.object)
            triple = (fact.subject, fact.predicate, fact.object)
            self.predicate_counts[fact.predicate] += 1
            self.predicate_true[fact.predicate] += y
            self.subject_counts[fact.subject] += 1
            self.subject_true[fact.subject] += y
            self.object_counts[fact.object] += 1
            self.object_true[fact.object] += y
            self.subject_predicate_counts[sp] += 1
            self.subject_predicate_true[sp] += y
            self.predicate_object_counts[po] += 1
            self.predicate_object_true[po] += y
            self.triple_counts[triple] += 1
            self.triple_true[triple] += y
            if y >= 0.5:
                self.true_objects_by_subject_predicate[sp].add(fact.object)
                true_object_sets[sp].add(fact.object)
        per_predicate_object_counts: dict[str, list[int]] = defaultdict(list)
        for (_subject, predicate), objects in true_object_sets.items():
            per_predicate_object_counts[predicate].append(len(objects))
        for predicate, counts in per_predicate_object_counts.items():
            single_object_ratio = sum(1 for count in counts if count <= 1) / len(counts)
            average_objects = sum(counts) / len(counts)
            if single_object_ratio >= 0.9 and average_objects <= 1.2:
                self.functional_predicates.add(predicate)

    # Returns a smoothed truth rate for one feature.
    def rate(self, true_counter: Counter, count_counter: Counter, key, strength: float = 4.0) -> float:
        return beta_mean(true_counter[key], count_counter[key], self.global_rate, strength)

    # Predicts a truth score for one fact.
    def score(self, fact: Fact) -> float:
        sp = (fact.subject, fact.predicate)
        po = (fact.predicate, fact.object)
        triple = (fact.subject, fact.predicate, fact.object)
        components: list[tuple[float, float]] = [
            (0.35, self.rate(self.predicate_true, self.predicate_counts, fact.predicate, strength=8.0)),
            (0.16, self.rate(self.subject_true, self.subject_counts, fact.subject, strength=6.0)),
            (0.16, self.rate(self.object_true, self.object_counts, fact.object, strength=6.0)),
            (0.20, self.rate(self.predicate_object_true, self.predicate_object_counts, po, strength=5.0)),
            (0.25, self.rate(self.subject_predicate_true, self.subject_predicate_counts, sp, strength=5.0)),
        ]
        if self.triple_counts[triple]:
            components.append((0.75, self.rate(self.triple_true, self.triple_counts, triple, strength=2.0)))
        true_objects = self.true_objects_by_subject_predicate.get(sp, set())
        if fact.object in true_objects:
            components.append((0.70, 0.97))
        elif true_objects and fact.predicate in self.functional_predicates:
            components.append((0.55, 0.08))
        elif true_objects:
            components.append((0.15, 0.35))
        subject_tokens = token_set(fact.subject)
        object_tokens = token_set(fact.object)
        if subject_tokens and object_tokens:
            overlap = len(subject_tokens & object_tokens) / len(subject_tokens | object_tokens)
            components.append((0.05, min(0.9, 0.35 + overlap)))
        weight_sum = sum(weight for weight, _value in components)
        logit_average = sum(weight * logit(value) for weight, value in components) / weight_sum
        return min(max(sigmoid(logit_average), 0.0), 1.0)

# Writes scores in the GERBIL TTL result format.
def write_result(path: Path, facts: Iterable[Fact], scorer: FactScorer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for fact in facts:
            score = scorer.score(fact)
            handle.write(f'<{fact.fact_uri}> <{TRUTH_VALUE}> "{score:.6f}"^^<{XSD_DOUBLE}> .\n')

# Reads command-line arguments.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate GERBIL fact-checking scores.")
    parser.add_argument("--train", type=Path, required=True, help="Path to labeled training .nt/.ttl file.")
    parser.add_argument("--test", type=Path, required=True, help="Path to unlabeled test .nt/.ttl file.")
    parser.add_argument("--output", type=Path, default=Path("outputs/result.ttl"), help="Output result TTL path.")
    return parser.parse_args()

# Runs the full parse, train, score, and write pipeline.
def main() -> None:
    args = parse_args()
    train_facts = parse_statement_file(args.train)
    test_facts = parse_statement_file(args.test)
    scorer = FactScorer()
    scorer.fit(train_facts)
    write_result(args.output, test_facts, scorer)
    print(f"Loaded {len(train_facts)} training facts.")
    print(f"Scored {len(test_facts)} test facts.")
    print(f"Wrote {args.output}")

if __name__ == "__main__":
    main()
