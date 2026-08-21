from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import chain
from math import log, log2
from random import Random
from typing import Mapping, Sequence
import re

BOS = "<bos>"
EOS = "<eos>"
UNK = "<unk>"
ANSWER_SLOT = "<answer>"
EPS = 1e-12


class TokenSymbolSpace:
    TOKEN_RE = re.compile(r"<[^>]+>|[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*|[一-龯々〆ヵヶぁ-んァ-ヶー]+|[^\w\s]", re.UNICODE)

    def __init__(self) -> None:
        self.token_to_id: dict[str, int] = {}
        self.id_to_token: list[str] = []
        for token in (BOS, EOS, UNK, ANSWER_SLOT):
            self.add(token)

    @staticmethod
    def normalize(token: str) -> str:
        if token.startswith("<") and token.endswith(">"):
            return token.lower()
        if re.fullmatch(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", token):
            return token.lower()
        return token

    def tokenize(self, text: str) -> list[str]:
        return [self.normalize(t) for t in self.TOKEN_RE.findall(text)]

    def add(self, token: str) -> int:
        token = self.normalize(token)
        if token not in self.token_to_id:
            self.token_to_id[token] = len(self.id_to_token)
            self.id_to_token.append(token)
        return self.token_to_id[token]

    def fit(self, texts: Sequence[str]) -> None:
        for text in texts:
            for token in self.tokenize(text):
                self.add(token)

    def encode(self, text: str) -> list[int]:
        return [self.token_to_id.get(token, self.token_to_id[UNK]) for token in self.tokenize(text)]

    def decode_tokens(self, tokens: Sequence[str]) -> str:
        out = ""
        no_space_before = {".", ",", "!", "?", ":", ";", "。", "、", "！", "？", ")", "]"}
        for token in tokens:
            if token in {BOS, EOS}:
                continue
            if not out:
                out = token
            elif token in no_space_before:
                out += token
            else:
                out += " " + token
        return out

    def __len__(self) -> int:
        return len(self.id_to_token)


@dataclass(frozen=True)
class SequenceSample:
    features: dict[str, str]
    target: str


@dataclass
class TreeNode:
    counts: dict[str, int]
    feature: str | None = None
    children: dict[str, "TreeNode"] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return self.feature is None or not self.children


class CategoricalDecisionForest:
    """明示的なカテゴリ特徴から次記号分布を学習する非ニューラル決定木アンサンブル。"""

    def __init__(self, vocabulary: Sequence[str], n_trees: int = 19, max_depth: int = 7, seed: int = 20260821, alpha: float = 0.03) -> None:
        self.vocabulary = tuple(sorted(set(vocabulary)))
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.seed = seed
        self.alpha = alpha
        self.trees: list[TreeNode] = []
        self.fitted = False
        self.training_sample_count = 0
        self.feature_names: tuple[str, ...] = ()

    @staticmethod
    def _entropy(samples: Sequence[SequenceSample]) -> float:
        if not samples:
            return 0.0
        counts = Counter(sample.target for sample in samples)
        total = len(samples)
        return -sum((count / total) * log2(count / total) for count in counts.values())

    def _gain(self, samples: Sequence[SequenceSample], feature: str) -> float:
        base = self._entropy(samples)
        groups: dict[str, list[SequenceSample]] = defaultdict(list)
        for sample in samples:
            groups[sample.features.get(feature, "<missing>")].append(sample)
        weighted = sum((len(group) / len(samples)) * self._entropy(group) for group in groups.values())
        return base - weighted

    def _build(self, samples: Sequence[SequenceSample], features: Sequence[str], depth: int, rng: Random) -> TreeNode:
        node = TreeNode(dict(Counter(sample.target for sample in samples)))
        if depth >= self.max_depth or len(node.counts) <= 1 or not features:
            return node
        feature_list = list(features)
        rng.shuffle(feature_list)
        subset = feature_list[: max(1, int(len(feature_list) ** 0.5))]
        ranked = sorted(((self._gain(samples, f), f) for f in subset), key=lambda x: (-x[0], x[1]))
        gain, feature = ranked[0]
        if gain <= EPS:
            ranked = sorted(((self._gain(samples, f), f) for f in features), key=lambda x: (-x[0], x[1]))
            gain, feature = ranked[0]
            if gain <= EPS:
                return node
        groups: dict[str, list[SequenceSample]] = defaultdict(list)
        for sample in samples:
            groups[sample.features.get(feature, "<missing>")].append(sample)
        if len(groups) <= 1:
            return node
        node.feature = feature
        remaining = [f for f in features if f != feature]
        for value, group in sorted(groups.items()):
            node.children[value] = self._build(group, remaining, depth + 1, rng)
        return node

    def fit(self, samples: Sequence[SequenceSample]) -> None:
        if not samples:
            raise ValueError("sequence fitting requires samples")
        self.training_sample_count = len(samples)
        self.feature_names = tuple(sorted(set(chain.from_iterable(sample.features.keys() for sample in samples))))
        rng = Random(self.seed)
        self.trees = []
        for index in range(self.n_trees):
            bootstrap = [samples[rng.randrange(len(samples))] for _ in range(len(samples))]
            self.trees.append(self._build(bootstrap, self.feature_names, 0, Random(self.seed + 7919 * (index + 1))))
        self.fitted = True

    def _distribution(self, node: TreeNode) -> dict[str, float]:
        total = sum(node.counts.values()) + self.alpha * len(self.vocabulary)
        return {token: (node.counts.get(token, 0) + self.alpha) / total for token in self.vocabulary}

    def _predict_tree(self, node: TreeNode, features: Mapping[str, str]) -> dict[str, float]:
        current = node
        while not current.is_leaf:
            assert current.feature is not None
            child = current.children.get(features.get(current.feature, "<missing>"))
            if child is None:
                break
            current = child
        return self._distribution(current)

    def predict_distribution(self, features: Mapping[str, str], allowed_tokens: Sequence[str] | None = None) -> dict[str, float]:
        tokens = tuple(allowed_tokens) if allowed_tokens else self.vocabulary
        if not self.fitted or not self.trees:
            return {token: 1.0 / len(tokens) for token in tokens} if tokens else {}
        aggregate = {token: 0.0 for token in self.vocabulary}
        for tree in self.trees:
            for token, probability in self._predict_tree(tree, features).items():
                aggregate[token] += probability
        aggregate = {token: value / len(self.trees) for token, value in aggregate.items()}
        if allowed_tokens is not None:
            allowed = set(allowed_tokens)
            aggregate = {token: p for token, p in aggregate.items() if token in allowed}
        total = sum(aggregate.values())
        if total <= EPS:
            return {token: 1.0 / len(tokens) for token in tokens} if tokens else {}
        return {token: p / total for token, p in aggregate.items()}

    def parameter_count(self) -> int:
        def count(node: TreeNode) -> int:
            return 1 + len(node.counts) + sum(1 + count(child) for child in node.children.values())
        return sum(count(tree) for tree in self.trees)

    def nll(self, samples: Sequence[SequenceSample]) -> float:
        if not samples:
            return 0.0
        return sum(-log(max(self.predict_distribution(sample.features).get(sample.target, EPS), EPS)) for sample in samples) / len(samples)


@dataclass(frozen=True)
class GenerationPlan:
    decision: str
    intent: str
    answer: str
    relation: str
    has_proof: bool
    language: str = "en"


class ConditionalSurface:
    def __init__(self, token_space: TokenSymbolSpace, transform: CategoricalDecisionForest) -> None:
        self.token_space = token_space
        self.transform = transform

    @staticmethod
    def context_features(prefix: Sequence[str], plan: GenerationPlan) -> dict[str, str]:
        prev1 = prefix[-1] if prefix else BOS
        prev2 = "|".join(prefix[-2:]) if len(prefix) >= 2 else BOS + "|" + prev1
        return {
            "decision": plan.decision,
            "intent": plan.intent,
            "relation": plan.relation or "none",
            "proof": "1" if plan.has_proof else "0",
            "language": plan.language,
            "position": str(len(prefix)),
            "prev1": prev1,
            "prev2": prev2,
        }

    def next_distribution(self, prefix: Sequence[str], plan: GenerationPlan, allowed_tokens: Sequence[str] | None = None) -> dict[str, float]:
        return self.transform.predict_distribution(self.context_features(prefix, plan), allowed_tokens)


class NonNeuralDecoder:
    APPROVE_PATHS = (
        ("the", "answer", "is", ANSWER_SLOT, ".", EOS),
        (ANSWER_SLOT, ".", EOS),
        ("evidence", "supports", ANSWER_SLOT, ".", EOS),
    )
    MEMORY_PATHS = (("the", "stored", "value", "is", ANSWER_SLOT, ".", EOS), (ANSWER_SLOT, ".", EOS))
    RISK_PATHS = (("the", "identified", "risk", "is", ANSWER_SLOT, ".", EOS), ("the", "answer", "is", ANSWER_SLOT, ".", EOS))
    GRID_PATHS = (("the", "leftmost", "object", "is", ANSWER_SLOT, ".", EOS), (ANSWER_SLOT, ".", EOS))
    SUSPEND_PATHS = (("insufficient", "evidence", ".", EOS), ("the", "result", "is", "suspended", ".", EOS))

    def __init__(self, token_space: TokenSymbolSpace, surface: ConditionalSurface) -> None:
        self.token_space = token_space
        self.surface = surface

    def paths_for(self, plan: GenerationPlan) -> tuple[tuple[str, ...], ...]:
        if plan.decision != "APPROVE":
            return self.SUSPEND_PATHS
        if plan.intent in {"memory_recall", "memory_write"}:
            return self.MEMORY_PATHS
        if plan.intent == "risk_reasoning":
            return self.RISK_PATHS
        if plan.intent == "grid_relation":
            return self.GRID_PATHS
        return self.APPROVE_PATHS

    def decode(self, plan: GenerationPlan, beam_width: int = 4) -> tuple[str, list[dict[str, object]]]:
        paths = self.paths_for(plan)
        beams: list[tuple[tuple[str, ...], float]] = [((), 0.0)]
        trace: list[dict[str, object]] = []
        for step in range(max(len(path) for path in paths) + 1):
            expanded: list[tuple[tuple[str, ...], float]] = []
            for prefix, score in beams:
                matching = [path for path in paths if path[: len(prefix)] == prefix]
                if not matching:
                    continue
                if prefix and prefix[-1] == EOS:
                    expanded.append((prefix, score))
                    continue
                allowed = sorted({path[len(prefix)] for path in matching if len(path) > len(prefix)})
                for token, probability in sorted(self.surface.next_distribution(prefix, plan, allowed).items(), key=lambda x: (-x[1], x[0])):
                    expanded.append((prefix + (token,), score + log(max(probability, EPS))))
            if not expanded:
                break
            beams = sorted(expanded, key=lambda x: (-x[1], x[0]))[:beam_width]
            trace.append({"op": "DECODE_STEP", "step": step, "beam_count": len(beams)})
            if all(prefix and prefix[-1] == EOS for prefix, _ in beams):
                break
        completed = [beam for beam in beams if beam[0] and beam[0][-1] == EOS]
        if not completed:
            raise RuntimeError("decoder failed to reach EOS")
        tokens, _ = max(completed, key=lambda x: x[1])
        emitted: list[str] = []
        for token in tokens:
            emitted.extend(self.token_space.tokenize(plan.answer)) if token == ANSWER_SLOT else emitted.append(token)
        text = self.token_space.decode_tokens(emitted)
        return (text[0].upper() + text[1:] if text else text), trace


class NonNeuralGenerator:
    def __init__(self, token_space: TokenSymbolSpace, transform: CategoricalDecisionForest) -> None:
        self.token_space = token_space
        self.transform = transform
        self.surface = ConditionalSurface(token_space, transform)
        self.decoder = NonNeuralDecoder(token_space, self.surface)

    def generate(self, plan: GenerationPlan) -> tuple[str, list[dict[str, object]]]:
        text, decoder_trace = self.decoder.decode(plan)
        return text, [
            {"op": "CONDITIONAL_LINGUISTIC_OUTPUT_SURFACE", "parameter_count": self.transform.parameter_count()},
            *decoder_trace,
            {"op": "DECODING_OR_EMISSION_INTERFACE", "text": text},
        ]


def generation_training_sequences() -> list[tuple[GenerationPlan, tuple[str, ...]]]:
    result: list[tuple[GenerationPlan, tuple[str, ...]]] = []
    for intent, relation, paths in (
        ("knowledge_query", "capability", NonNeuralDecoder.APPROVE_PATHS),
        ("memory_recall", "memory_value", NonNeuralDecoder.MEMORY_PATHS),
        ("memory_write", "memory_write", NonNeuralDecoder.MEMORY_PATHS),
        ("risk_reasoning", "risk", NonNeuralDecoder.RISK_PATHS),
        ("grid_relation", "leftmost_color", NonNeuralDecoder.GRID_PATHS),
    ):
        plan = GenerationPlan("APPROVE", intent, ANSWER_SLOT, relation, True)
        for _ in range(4):
            for path in paths:
                result.append((plan, path))
    suspend = GenerationPlan("SUSPEND", "unknown", "", "none", False)
    for _ in range(10):
        for path in NonNeuralDecoder.SUSPEND_PATHS:
            result.append((suspend, path))
    return result


def build_generator() -> tuple[NonNeuralGenerator, list[SequenceSample], dict[str, float | int]]:
    token_space = TokenSymbolSpace()
    sequences = generation_training_sequences()
    token_space.fit([" ".join(path) for _, path in sequences])
    transform = CategoricalDecisionForest(token_space.id_to_token)
    generator = NonNeuralGenerator(token_space, transform)
    samples: list[SequenceSample] = []
    for plan, sequence in sequences:
        prefix: list[str] = []
        for target in sequence:
            samples.append(SequenceSample(generator.surface.context_features(prefix, plan), target))
            prefix.append(target)
    before = transform.nll(samples)
    transform.fit(samples)
    after = transform.nll(samples)
    return generator, samples, {
        "before_nll": before,
        "after_nll": after,
        "parameter_count": transform.parameter_count(),
        "sample_count": len(samples),
        "vocabulary_size": len(token_space),
    }
