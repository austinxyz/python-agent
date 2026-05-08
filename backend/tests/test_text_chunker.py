"""Unit tests for the shared text-chunking helper.

The helper used to live inline in `ingest_pipeline.chunk_node`. After
extraction (this change) both the knowledge ingest path and the private
entries route call the same function — these tests pin the contract.
"""
import pytest


class TestChunkText:
    def test_short_content_yields_single_chunk(self):
        from app.graphs.text_chunker import chunk_text
        result = chunk_text("hello world")
        assert result == [{"text": "hello world", "chunk_index": 0}]

    def test_empty_content_yields_single_empty_chunk(self):
        from app.graphs.text_chunker import chunk_text
        result = chunk_text("")
        assert result == [{"text": "", "chunk_index": 0}]

    def test_long_content_yields_multiple_chunks(self):
        from app.graphs.text_chunker import chunk_text, CHUNK_SIZE
        # Build content > 2 × CHUNK_SIZE so we definitely get multiple chunks
        para = "段落内容。" * 200          # 6 chars × 200 = 1200 chars per paragraph
        many = "\n\n".join([para] * 10)   # ~12000 chars total — well over 2 × CHUNK_SIZE=2000
        chunks = chunk_text(many)
        assert len(chunks) >= 2
        # chunk_index is sequential starting at 0
        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
        # The accumulator can hold up to ~CHUNK_SIZE worth of paragraphs
        # (joined with \n\n separators) before a new part trips the
        # >size check; the previous chunk's overlap is then prepended.
        # Bound chunks at 2 * CHUNK_SIZE + CHUNK_OVERLAP — well below the
        # 8192-token embedding limit either way.
        from app.graphs.text_chunker import CHUNK_OVERLAP
        for c in chunks:
            assert len(c["text"]) <= 2 * CHUNK_SIZE + CHUNK_OVERLAP

    def test_consecutive_chunks_share_overlap(self):
        from app.graphs.text_chunker import chunk_text, CHUNK_OVERLAP
        # Long single paragraph forces sentence-split + overlap
        para = "Sentence number {}. ".format
        long = " ".join(para(i) for i in range(500))   # ~10000 chars
        chunks = chunk_text(long)
        assert len(chunks) >= 2
        # Each non-first chunk's leading prefix appears at the END of the prior chunk
        for prev, cur in zip(chunks, chunks[1:]):
            head_of_cur = cur["text"][:CHUNK_OVERLAP]
            tail_of_prev = prev["text"][-CHUNK_OVERLAP:]
            # They should share at least some text (exact overlap may differ
            # because the chunker re-emits prev_tail before the next body)
            assert head_of_cur == tail_of_prev or head_of_cur in prev["text"]


class TestParityWithIngestNode:
    """The refactor MUST keep `chunk_node` output byte-identical for any
    knowledge-ingest input — otherwise existing Qdrant data would diverge
    from what the next ingest writes."""

    def test_chunk_node_delegates_to_chunk_text(self):
        from app.graphs.ingest_pipeline import chunk_node

        para = "段落 " * 250
        many = "\n\n".join([para] * 8)
        node_out = chunk_node({"raw_content": many})

        from app.graphs.text_chunker import chunk_text
        helper_out = chunk_text(many)

        assert node_out == {"chunks": helper_out}

    def test_chunk_node_handles_short_input_unchanged(self):
        from app.graphs.ingest_pipeline import chunk_node
        out = chunk_node({"raw_content": "short text"})
        assert out == {"chunks": [{"text": "short text", "chunk_index": 0}]}
