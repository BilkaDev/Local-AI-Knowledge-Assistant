import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rag.generation import generate_answer
from rag.retrieval import RetrievalResult, RetrievedChunk


class GenerationTests(unittest.TestCase):
    @patch("rag.generation.retrieve_similar_chunks")
    @patch("rag.generation._create_ollama_client")
    def test_generate_answer_returns_text_and_sources(
        self,
        create_client_mock: Mock,
        retrieve_mock: Mock,
    ) -> None:
        retrieve_mock.return_value = RetrievalResult(
            question="What is policy?",
            requested_top_k=2,
            retrieval_time_ms=12.5,
            chunks=[
                RetrievedChunk(
                    chunk_id="doc1-0001",
                    source_file="policy.txt",
                    text="Policy requires approval.",
                    char_start=0,
                    char_end=24,
                    distance=0.11,
                )
            ],
        )
        ollama_client = Mock()
        ollama_client.chat.return_value = {"message": {"content": "Approval is required."}}
        create_client_mock.return_value = ollama_client

        logs: list[str] = []
        result = generate_answer(
            question="What is policy?",
            top_k=2,
            collection_name="rag_chunks",
            persist_dir=Path("artifacts/chroma"),
            embedding_model="nomic-embed-text",
            llm_model="llama3",
            max_context_distance=0.5,
            log_fn=logs.append,
        )

        self.assertEqual("Approval is required.", result.answer_text)
        self.assertEqual(1, result.used_chunks)
        self.assertEqual("doc1-0001", result.sources[0].chunk_id)
        self.assertEqual("policy.txt", result.sources[0].source_file)
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(1, len(logs))
        self.assertIn("[generation]", logs[0])
        ollama_client.chat.assert_called_once()

    @patch("rag.generation.retrieve_similar_chunks")
    @patch("rag.generation._create_ollama_client")
    def test_generate_answer_fallback_when_no_context(
        self,
        create_client_mock: Mock,
        retrieve_mock: Mock,
    ) -> None:
        retrieve_mock.return_value = RetrievalResult(
            question="Question",
            requested_top_k=3,
            retrieval_time_ms=9.1,
            chunks=[],
        )

        result = generate_answer(
            question="Question",
            top_k=3,
            collection_name="rag_chunks",
            persist_dir=Path("artifacts/chroma"),
            embedding_model="nomic-embed-text",
            llm_model="llama3",
            log_fn=None,
        )

        self.assertEqual("no_context", result.fallback_reason)
        self.assertEqual(0, result.used_chunks)
        self.assertEqual([], result.sources)
        self.assertEqual(0.0, result.generation_time_ms)
        create_client_mock.assert_not_called()

    @patch("rag.generation.retrieve_similar_chunks")
    @patch("rag.generation._create_ollama_client")
    def test_generate_answer_fallback_when_all_chunks_above_threshold(
        self,
        create_client_mock: Mock,
        retrieve_mock: Mock,
    ) -> None:
        retrieve_mock.return_value = RetrievalResult(
            question="Question",
            requested_top_k=2,
            retrieval_time_ms=7.4,
            chunks=[
                RetrievedChunk(
                    chunk_id="doc1-0001",
                    source_file="file1.txt",
                    text="One",
                    char_start=0,
                    char_end=3,
                    distance=0.8,
                ),
                RetrievedChunk(
                    chunk_id="doc2-0001",
                    source_file="file2.txt",
                    text="Two",
                    char_start=4,
                    char_end=7,
                    distance=0.9,
                ),
            ],
        )

        result = generate_answer(
            question="Question",
            top_k=2,
            collection_name="rag_chunks",
            persist_dir=Path("artifacts/chroma"),
            embedding_model="nomic-embed-text",
            llm_model="llama3",
            max_context_distance=0.5,
            log_fn=None,
        )

        self.assertEqual("low_relevance", result.fallback_reason)
        self.assertEqual(0, result.used_chunks)
        create_client_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
