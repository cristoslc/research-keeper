"""Tests for transport resolution and prefixes."""

from __future__ import annotations

import pytest
from pathlib import Path

from research_keeper.ports.transport import (
    TransportResult,
    parse_transport,
    TRANSPORT_PREFIXES,
)
from research_keeper.adapters.transports.transports import (
    FileTransport,
    UrlTransport,
    TextTransport,
)
from research_keeper.adapters.transports.resolver import resolve_transport


class TestParseTransport:
    """Test prefix parsing for transport inputs."""

    def test_wormhole_prefix(self):
        prefix, payload = parse_transport("wormhole:7-purple-elephant")
        assert prefix == "wormhole"
        assert payload == "7-purple-elephant"

    def test_file_prefix(self):
        prefix, payload = parse_transport("file:/tmp/paper.pdf")
        assert prefix == "file"
        assert payload == "/tmp/paper.pdf"

    def test_url_prefix(self):
        prefix, payload = parse_transport("url:https://example.com")
        assert prefix == "url"
        assert payload == "https://example.com"

    def test_text_prefix(self):
        prefix, payload = parse_transport("text:hello world")
        assert prefix == "text"
        assert payload == "hello world"

    def test_no_prefix_bare_path(self):
        prefix, payload = parse_transport("./paper.pdf")
        assert prefix is None
        assert payload == "./paper.pdf"

    def test_no_prefix_url(self):
        prefix, payload = parse_transport("https://example.com")
        assert prefix is None
        assert payload == "https://example.com"

    def test_text_prefix_dash(self):
        prefix, payload = parse_transport("text:-")
        assert prefix == "text"
        assert payload == "-"


class TestFileTransport:
    """Test file: transport."""

    def test_existing_file(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Hello")
        transport = FileTransport()
        result = transport.receive(str(f))
        assert not result.is_content
        assert Path(result.resolved).exists()

    def test_missing_file_raises(self):
        transport = FileTransport()
        with pytest.raises(FileNotFoundError):
            transport.receive("/nonexistent/file.md")

    def test_directory_raises(self, tmp_path: Path):
        transport = FileTransport()
        with pytest.raises(ValueError, match="Not a file"):
            transport.receive(str(tmp_path))


class TestUrlTransport:
    """Test url: transport."""

    def test_https_url(self):
        transport = UrlTransport()
        result = transport.receive("https://example.com/article")
        assert not result.is_content
        assert result.resolved == "https://example.com/article"
        assert result.metadata["origin"] == "https://example.com/article"

    def test_bare_domain(self):
        transport = UrlTransport()
        result = transport.receive("example.com/article")
        assert result.resolved == "https://example.com/article"

    def test_http_url(self):
        transport = UrlTransport()
        result = transport.receive("http://example.com")
        assert result.resolved == "http://example.com"


class TestTextTransport:
    """Test text: transport."""

    def test_basic_text(self):
        transport = TextTransport()
        result = transport.receive("Hello world")
        assert result.is_content
        assert result.resolved == "Hello world"

    def test_multiline_text(self):
        transport = TextTransport()
        result = transport.receive("Line 1\nLine 2")
        assert result.is_content
        assert "Line 1" in result.resolved


class TestResolveTransport:
    """Test the top-level transport resolver."""

    def test_bare_existing_file(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Hello")
        result = resolve_transport(str(f))
        assert not result.is_content
        assert Path(result.resolved).exists()

    def test_bare_url(self):
        result = resolve_transport("https://example.com")
        assert not result.is_content
        assert result.resolved == "https://example.com"
        assert result.metadata["origin"] == "https://example.com"

    def test_text_prefix(self):
        result = resolve_transport("text:hello world")
        assert result.is_content
        assert result.resolved == "hello world"

    def test_url_prefix(self):
        result = resolve_transport("url:https://example.com")
        assert not result.is_content
        assert result.resolved == "https://example.com"

    def test_file_prefix(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Hello")
        result = resolve_transport(f"file:{f}")
        assert not result.is_content
        assert Path(result.resolved).exists()

    def test_plain_text_falls_through(self):
        result = resolve_transport("just some text")
        assert result.is_content is False
        assert result.resolved == "just some text"

    def test_unknown_prefix_raises(self):
        with pytest.raises(ValueError, match="Unknown transport prefix"):
            resolve_transport("ftp:something")
