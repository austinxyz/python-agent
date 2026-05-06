import threading
import pytest
from app.services.job_registry import JobRegistry


class TestJobRegistryBasics:
    def test_create_initialises_running_status(self):
        registry = JobRegistry()
        registry.create("job-1")
        state = registry.get("job-1")
        assert state == {"status": "running"}

    def test_get_returns_current_state(self):
        registry = JobRegistry()
        registry.create("job-2")
        state = registry.get("job-2")
        assert state is not None
        assert state["status"] == "running"

    def test_update_merges_patch_into_state(self):
        registry = JobRegistry()
        registry.create("job-3")
        registry.update("job-3", {"status": "completed", "chunk_count": 5})
        state = registry.get("job-3")
        assert state["status"] == "completed"
        assert state["chunk_count"] == 5

    def test_get_unknown_id_returns_none(self):
        registry = JobRegistry()
        assert registry.get("nonexistent") is None

    def test_update_preserves_existing_keys(self):
        registry = JobRegistry()
        registry.create("job-4")
        registry.update("job-4", {"file_id": "abc"})
        registry.update("job-4", {"chunk_count": 3})
        state = registry.get("job-4")
        assert state["file_id"] == "abc"
        assert state["chunk_count"] == 3
        assert state["status"] == "running"


class TestJobRegistryErrorCases:
    def test_create_duplicate_raises_value_error(self):
        registry = JobRegistry()
        registry.create("dup")
        with pytest.raises(ValueError, match="dup"):
            registry.create("dup")

    def test_update_unknown_job_raises_key_error(self):
        registry = JobRegistry()
        with pytest.raises(KeyError):
            registry.update("ghost", {"status": "completed"})

    def test_get_returns_deep_copy_not_reference(self):
        registry = JobRegistry()
        registry.create("copy-test")
        registry.update("copy-test", {"tags": ["a", "b"]})
        state = registry.get("copy-test")
        state["tags"].append("c")
        assert registry.get("copy-test")["tags"] == ["a", "b"]


class TestJobRegistryConcurrency:
    def test_concurrent_updates_to_same_job_do_not_lose_writes(self):
        registry = JobRegistry()
        registry.create("shared-job")
        num_threads = 50
        barrier = threading.Barrier(num_threads)

        def write_key(i):
            barrier.wait()
            registry.update("shared-job", {f"key_{i}": i})

        threads = [threading.Thread(target=write_key, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        state = registry.get("shared-job")
        assert len(state) == num_threads + 1  # +1 for "status"
        for i in range(num_threads):
            assert state[f"key_{i}"] == i
