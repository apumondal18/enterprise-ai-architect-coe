import redis
import os
import requests
import uuid
import hashlib

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")

DIMENSION = 384
INDEX_NAME = "semantic_cache"

TTL_SECONDS = 86400
EXPIRY_KEY = "semantic_cache:expiry"


class SemanticCache:

    def __init__(self):

        if not REDIS_URL:
            raise ValueError("REDIS_URL is missing from .env")

        if not EMBEDDING_API_URL:
            raise ValueError("EMBEDDING_API_URL is missing from .env")

        self.redis = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10
        )

        self.index_name = INDEX_NAME

    def create_index(self):

        self.redis.execute_command(
            "VECTOR.CREATE",
            self.index_name,
            "DIM", DIMENSION,
            "METRIC", "COSINE",
            "EXISTSOK"
        )

    def generate_embedding(self, query):

        response = requests.post(
            f"{EMBEDDING_API_URL}/embed",
            json={"texts": [query]},
            timeout=120
        )

        response.raise_for_status()

        embedding = response.json()["embeddings"][0]

        if len(embedding) != DIMENSION:
            raise ValueError(
                f"Expected {DIMENSION} dimensions, "
                f"received {len(embedding)}"
            )

        return embedding

    def _get_query_hash(self, query):

        normalized_query = " ".join(query.lower().split())

        return hashlib.sha256(
            normalized_query.encode("utf-8")
        ).hexdigest()

    def store(
        self,
        query,
        embedding,
        answer,
        ttl_seconds=TTL_SECONDS
    ):

        if len(embedding) != DIMENSION:
            raise ValueError("Incorrect embedding dimension")

        if ttl_seconds <= 0:
            raise ValueError("TTL must be greater than zero")

        query_hash = self._get_query_hash(query)

        query_hash_key = f"semantic_cache:query:{query_hash}"

        existing_id = self.redis.get(query_hash_key)

        # Exact duplicate query already exists
        if existing_id:

            existing_answer = self.redis.get(
                f"answer:{existing_id}"
            )

            if existing_answer is not None:

                self.redis.set(
                    f"answer:{existing_id}",
                    answer,
                    ex=ttl_seconds
                )

                self.redis.set(
                    f"query:{existing_id}",
                    query,
                    ex=ttl_seconds
                )

                current_time = int(self.redis.time()[0])

                self.redis.zadd(
                    EXPIRY_KEY,
                    {
                        existing_id:
                        current_time + ttl_seconds
                    }
                )

                self.redis.expire(
                    query_hash_key,
                    ttl_seconds
                )

                print("Existing cache entry updated:", existing_id)

                return existing_id

            # Remove stale mapping
            self.redis.execute_command(
                "VECTOR.DEL",
                self.index_name,
                existing_id
            )

            self.redis.delete(
                f"query:{existing_id}",
                query_hash_key
            )

            self.redis.zrem(
                EXPIRY_KEY,
                existing_id
            )

        # Create a new entry
        cache_id = str(uuid.uuid4())

        self.redis.execute_command(
            "VECTOR.ADD",
            self.index_name,
            cache_id,
            "VALUES",
            DIMENSION,
            *embedding
        )

        self.redis.set(
            f"answer:{cache_id}",
            answer,
            ex=ttl_seconds
        )

        self.redis.set(
            f"query:{cache_id}",
            query,
            ex=ttl_seconds
        )

        self.redis.set(
            query_hash_key,
            cache_id,
            ex=ttl_seconds
        )

        current_time = int(self.redis.time()[0])

        self.redis.zadd(
            EXPIRY_KEY,
            {
                cache_id:
                current_time + ttl_seconds
            }
        )

        print("New cache entry created:", cache_id)

        return cache_id

    def search(self, query_embedding, threshold=0.92):

        if len(query_embedding) != DIMENSION:
            raise ValueError("Incorrect embedding dimension")

        results = self.redis.execute_command(
            "VECTOR.QUERY",
            self.index_name,
            "TOPK", 5,
            "VALUES", DIMENSION,
            *query_embedding
        )

        if not results:
            return None

        for result in results:

            cache_id = result[0]

            upstash_score = float(result[1])

            cosine_similarity = (2 * upstash_score) - 1

            print(
                f"Cache ID: {cache_id}, "
                f"Cosine similarity: {cosine_similarity:.4f}"
            )

            if cosine_similarity >= threshold:

                answer = self.redis.get(
                    f"answer:{cache_id}"
                )

                if answer is not None:
                    return answer

        return None

    def delete_expired(self):

        current_time = int(self.redis.time()[0])

        expired_ids = self.redis.zrangebyscore(
            EXPIRY_KEY,
            "-inf",
            current_time
        )

        deleted_count = 0

        for cache_id in expired_ids:

            query = self.redis.get(f"query:{cache_id}")

            self.redis.execute_command(
                "VECTOR.DEL",
                self.index_name,
                cache_id
            )

            self.redis.delete(
                f"answer:{cache_id}",
                f"query:{cache_id}"
            )

            if query:

                query_hash = self._get_query_hash(query)

                query_hash_key = (
                    f"semantic_cache:query:{query_hash}"
                )

                # Only delete the mapping if it still
                # points to this expired entry.
                mapped_id = self.redis.get(query_hash_key)

                if mapped_id == cache_id:
                    self.redis.delete(query_hash_key)

            self.redis.zrem(
                EXPIRY_KEY,
                cache_id
            )

            deleted_count += 1

        return deleted_count
