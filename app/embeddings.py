import hashlib
import json
import math
import re

import requests


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


class EmbeddingError(RuntimeError):
    pass


class HashEmbeddingProvider:
    """Offline embedding fallback for development and repeatable tests.

    This is a signed feature-hashing representation, not a semantic foundation
    model. It keeps the vector pipeline operational without sending data to an
    external service and provides a stable baseline for evaluation.
    """

    def __init__(self, dimensions=384):
        self.dimensions = dimensions
        self.model_id = "local:feature-hash-v1:{}".format(dimensions)

    def embed(self, texts):
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text):
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text or "")]
        features = tokens + [
            "{}::{}".format(tokens[index], tokens[index + 1])
            for index in range(len(tokens) - 1)
        ]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return normalize(vector)


class OpenAIEmbeddingProvider:
    def __init__(self, api_key, model="text-embedding-3-small", session=None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        self.api_key = api_key
        self.model = model
        self.model_id = "openai:{}".format(model)
        self.session = session or requests.Session()

    def embed(self, texts):
        if not texts:
            return []
        try:
            response = self.session.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": "Bearer {}".format(self.api_key),
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            ordered = sorted(payload["data"], key=lambda item: item["index"])
            return [normalize(item["embedding"]) for item in ordered]
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError("Embedding request failed: {}".format(exc)) from exc


def create_embedding_provider(config):
    provider = (config.get("EMBEDDING_PROVIDER") or "local").lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=config.get("OPENAI_API_KEY", ""),
            model=config.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    if provider != "local":
        raise ValueError("EMBEDDING_PROVIDER must be 'local' or 'openai'")
    return HashEmbeddingProvider()


def cosine_similarity(left, right):
    if len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def normalize(vector):
    magnitude = math.sqrt(sum(value * value for value in vector))
    if not magnitude:
        return vector
    return [value / magnitude for value in vector]


def encode_vector(vector):
    return json.dumps(vector, separators=(",", ":"))


def decode_vector(value):
    return json.loads(value)

