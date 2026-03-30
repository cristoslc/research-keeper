from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.remote import RemoteResolver


class TestRemoteResolver:
    def test_is_remote_url_ssh(self):
        r = RemoteResolver("git@github.com:user/repo.git")
        assert r.is_remote is True

    def test_is_remote_url_https(self):
        r = RemoteResolver("https://github.com/user/repo.git")
        assert r.is_remote is True

    def test_is_local_path(self):
        r = RemoteResolver(".")
        assert r.is_remote is False

    def test_is_local_relative_path(self):
        r = RemoteResolver("./data")
        assert r.is_remote is False

    def test_is_local_absolute_path(self):
        r = RemoteResolver("/home/user/data")
        assert r.is_remote is False

    def test_cache_dir_deterministic(self):
        r = RemoteResolver("git@github.com:user/repo.git")
        assert r.cache_dir is not None
        # Same URL should produce same cache dir
        r2 = RemoteResolver("git@github.com:user/repo.git")
        assert r.cache_dir == r2.cache_dir

    def test_cache_dir_none_for_local(self):
        r = RemoteResolver(".")
        assert r.cache_dir is None

    def test_resolve_local_returns_path(self, tmp_path: Path):
        r = RemoteResolver(str(tmp_path))
        assert r.resolve() == tmp_path

    @patch("research_keeper.remote.subprocess")
    def test_clone_on_first_access(self, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        r = RemoteResolver("git@github.com:user/repo.git")

        with patch.object(r, "_clone_dir_exists", return_value=False):
            r.clone()
            mock_subprocess.run.assert_called_once()
            args = mock_subprocess.run.call_args[0][0]
            assert "git" in args
            assert "clone" in args

    @patch("research_keeper.remote.subprocess")
    def test_sync_runs_git_pull(self, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        r = RemoteResolver("git@github.com:user/repo.git")

        with patch.object(r, "_clone_dir_exists", return_value=True):
            r.sync()
            mock_subprocess.run.assert_called_once()
            args = mock_subprocess.run.call_args[0][0]
            assert "pull" in args

    @patch("research_keeper.remote.subprocess")
    def test_publish_runs_git_push(self, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        r = RemoteResolver("git@github.com:user/repo.git")

        with patch.object(r, "_clone_dir_exists", return_value=True):
            r.publish("Update from rk")
            calls = mock_subprocess.run.call_args_list
            # Should call git add, git commit, git push
            assert len(calls) >= 2

    def test_sync_noop_for_local(self, tmp_path: Path):
        r = RemoteResolver(str(tmp_path))
        # Should not raise
        r.sync()

    def test_publish_noop_for_local(self, tmp_path: Path):
        r = RemoteResolver(str(tmp_path))
        # Should not raise
        r.publish("test")
