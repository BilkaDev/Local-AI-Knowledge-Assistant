import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rag.retrieval import retrieve_similar_chunks


class FakeCollection:
    def __init__(self, count_value: int, query_payload: dict | None = None) -> None:
        self._count_value = count_value
        self._query_payload = query_payload or {}

    def count(self) -> int:
        return self._count_value

    def query(self, **_: object) -> dict:
        return self._query_payload


class RetrievalTests(unittest.TestCase):
    @patch("rag.retrieval._chromadb_module")
    def test_retrieve_returns_source_metadata_and_distance(self, chromadb_module_mock: Mock) -> None:
        collection = FakeCollection(
            count_value=2,
            query_payload={
                "documents": [["chunk text 1", "chunk text 2"]],
                "metadatas": [
                    [
                        {"chunk_id": "doc1-0001", "source_file": "doc1.txt", "char_start": 0, "char_end": 20},
                        {"chunk_id": "doc2-0001", "source_file": "doc2.pdf", "char_start": 21, "char_end": 45},
                    ]
                ],
                "distances": [[0.12, 0.34]],
            },
        )
        client = Mock()
        client.get_collection.return_value = collection
        chromadb_module_mock.return_value = Mock(PersistentClient=Mock(return_value=client))

        ollama_client = Mock()
        ollama_client.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        with patch("rag.retrieval._create_ollama_client", return_value=ollama_client):
            logs: list[str] = []
            result = retrieve_similar_chunks(
                question="What is in docs?",
                top_k=2,
                collection_name="rag_chunks",
                persist_dir=Path("artifacts/chroma"),
                embedding_model="nomic-embed-text",
                log_fn=logs.append,
            )

        self.assertEqual(2, len(result.chunks))
        self.assertEqual("doc1-0001", result.chunks[0].chunk_id)
        self.assertEqual("doc1.txt", result.chunks[0].source_file)
        self.assertEqual(0, result.chunks[0].char_start)
        self.assertEqual(20, result.chunks[0].char_end)
        self.assertEqual(0.12, result.chunks[0].distance)
        self.assertTrue(result.retrieval_time_ms >= 0.0)
        self.assertEqual(1, len(logs))
        self.assertIn("[retrieval]", logs[0])
        self.assertIn("returned_chunks=2", logs[0])

    def test_retrieve_rejects_invalid_top_k(self) -> None:
        with self.assertRaisesRegex(ValueError, "top_k"):
            retrieve_similar_chunks(
                question="test",
                top_k=0,
                collection_name="rag_chunks",
                persist_dir=Path("artifacts/chroma"),
                embedding_model="nomic-embed-text",
                log_fn=None,
            )

    @patch("rag.retrieval._chromadb_module")
    def test_retrieve_returns_empty_when_collection_is_empty(
        self, chromadb_module_mock: Mock
    ) -> None:
        client = Mock()
        client.get_collection.return_value = FakeCollection(count_value=0)
        chromadb_module_mock.return_value = Mock(PersistentClient=Mock(return_value=client))

        logs: list[str] = []
        result = retrieve_similar_chunks(
            question="Where is the policy?",
            top_k=3,
            collection_name="rag_chunks",
            persist_dir=Path("artifacts/chroma"),
            embedding_model="nomic-embed-text",
            log_fn=logs.append,
        )

        self.assertEqual([], result.chunks)
        self.assertEqual(3, result.requested_top_k)
        self.assertEqual(1, len(logs))
        self.assertIn("returned_chunks=0", logs[0])


if __name__ == "__main__":
    unittest.main()
