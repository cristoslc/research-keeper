# tests/test_normalizer_email.py
from __future__ import annotations

from pathlib import Path

import pytest

from research_keeper.adapters.normalizers.email import EmailNormalizer
from research_keeper.ports.normalizer import NormalizationError

SIMPLE_EML = """\
From: Alice Sender <alice@example.com>
To: Bob Recipient <bob@example.com>
Cc: Carol Copied <carol@example.com>
Subject: Quarterly Planning Notes
Date: Tue, 24 Sep 2026 10:30:00 +0000
Message-ID: <abc123@example.com>

Hi Bob,

Here are the quarterly planning notes we discussed.

Best,
Alice
"""


HTML_EML = """\
From: web@example.com
To: bob@example.com
Subject: HTML Newsletter
Date: Wed, 25 Sep 2026 08:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="BOUNDARY"

--BOUNDARY
Content-Type: text/plain; charset="utf-8"

Plain fallback body.
--BOUNDARY
Content-Type: text/html; charset="utf-8"

<html><body><h1>HTML Newsletter</h1><p>Rich <b>HTML</b> body.</p></body></html>
--BOUNDARY--
"""


ATTACHMENT_EML = """\
From: docs@example.com
To: bob@example.com
Subject: Report Attached
Date: Thu, 26 Sep 2026 09:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="MIXED"

--MIXED
Content-Type: text/plain; charset="utf-8"

Please find the report attached.
--MIXED
Content-Type: application/pdf; name="report.pdf"
Content-Disposition: attachment; filename="report.pdf"
Content-Transfer-Encoding: base64

JVBERi0xLjQK
--MIXED--
"""


class TestEmailNormalizerBasic:
    def test_plain_text_body_extracted(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        content, _meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert "quarterly planning notes we discussed" in content
        # The path must NOT appear as content
        assert str(eml) not in content

    def test_headers_in_content(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        content, _meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert "alice@example.com" in content
        assert "bob@example.com" in content
        assert "carol@example.com" in content
        assert "2026" in content

    def test_title_from_subject(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        _, meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert meta["title"] == "Quarterly Planning Notes"

    def test_published_from_date_header(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        _, meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert meta["published"] == "2026-09-24"

    def test_word_count(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        _, meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert int(meta["word_count"]) > 0


class TestEmailNormalizerBodyPreference:
    def test_prefers_text_plain(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(HTML_EML)

        content, _meta, _ = EmailNormalizer().normalize(str(eml), {})

        # text/plain part wins over text/html
        assert "Plain fallback body." in content
        assert "<b>" not in content

    def test_falls_back_to_stripped_html(self, tmp_path: Path):
        html_only = HTML_EML.replace(
            'Content-Type: text/plain; charset="utf-8"\n\nPlain fallback body.\n',
            'Content-Type: text/plain; charset="utf-8"\nContent-Disposition: attachment; filename="plain.txt"\n\nPlain fallback body.\n',
        )
        eml = tmp_path / "message.eml"
        eml.write_text(html_only)

        content, _meta, _ = EmailNormalizer().normalize(str(eml), {})

        # HTML part de-tagged: markup removed, text preserved
        assert "<html>" not in content
        assert "<b>" not in content
        assert "Rich" in content and "HTML" in content and "body." in content


class TestEmailNormalizerAttachments:
    def test_attachments_listed(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(ATTACHMENT_EML)

        content, meta, _ = EmailNormalizer().normalize(str(eml), {})

        assert "report.pdf" in content
        assert meta["attachments"] == "1"


class TestEmailNormalizerErrors:
    def test_missing_file_raises(self):
        with pytest.raises(NormalizationError, match="File not found"):
            EmailNormalizer().normalize("/nonexistent/path/message.eml", {})

    def test_unparseable_content_raises(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text("\x00\x01binary garbage not an email\x02")

        with pytest.raises(NormalizationError):
            EmailNormalizer().normalize(str(eml), {})

    def test_empty_body_and_headers_raises(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text("")

        with pytest.raises(NormalizationError):
            EmailNormalizer().normalize(str(eml), {})


class TestEmailNormalizerMetadataOverride:
    def test_provided_title_wins(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        _, meta, _ = EmailNormalizer().normalize(str(eml), {"title": "Custom"})

        assert meta["title"] == "Custom"

    def test_provided_published_wins(self, tmp_path: Path):
        eml = tmp_path / "message.eml"
        eml.write_text(SIMPLE_EML)

        _, meta, _ = EmailNormalizer().normalize(str(eml), {"published": "2020-01-01"})

        assert meta["published"] == "2020-01-01"