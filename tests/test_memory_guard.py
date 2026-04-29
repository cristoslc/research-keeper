from research_keeper.memory_guard import MemoryGuard, MemoryPressureError


class TestMemoryGuard:
    def test_check_passes_below_threshold(self, monkeypatch):
        def mock_virtual_memory():
            return type("VM", (), {"percent": 45.0})

        monkeypatch.setattr("psutil.virtual_memory", mock_virtual_memory)
        guard = MemoryGuard(threshold_percent=85.0)
        guard.check()  # should not raise

    def test_check_raises_at_threshold(self, monkeypatch):
        def mock_virtual_memory():
            return type("VM", (), {"percent": 85.0})

        monkeypatch.setattr("psutil.virtual_memory", mock_virtual_memory)
        guard = MemoryGuard(threshold_percent=85.0)
        try:
            guard.check()
            assert False, "Expected MemoryPressureError"
        except MemoryPressureError as exc:
            assert exc.current == 85.0
            assert exc.threshold == 85.0

    def test_check_raises_above_threshold(self, monkeypatch):
        def mock_virtual_memory():
            return type("VM", (), {"percent": 92.3})

        monkeypatch.setattr("psutil.virtual_memory", mock_virtual_memory)
        guard = MemoryGuard(threshold_percent=85.0)
        try:
            guard.check()
            assert False, "Expected MemoryPressureError"
        except MemoryPressureError as exc:
            assert exc.current == 92.3

    def test_custom_threshold(self, monkeypatch):
        def mock_virtual_memory():
            return type("VM", (), {"percent": 91.0})

        monkeypatch.setattr("psutil.virtual_memory", mock_virtual_memory)
        guard = MemoryGuard(threshold_percent=90.0)
        try:
            guard.check()
            assert False, "Expected MemoryPressureError"
        except MemoryPressureError as exc:
            assert exc.threshold == 90.0

    def test_default_threshold_is_85(self):
        guard = MemoryGuard()
        assert guard._threshold == 85.0
