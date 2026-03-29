from __future__ import annotations
from research_keeper.slugify import slugify

def test_basic_slugify():
    assert slugify("Hello World") == "hello-world"

def test_special_characters_removed():
    assert slugify("What's New? (2026)") == "whats-new-2026"

def test_url_slugify():
    assert slugify("https://example.com/blog/my-great-post") == "my-great-post"

def test_long_title_truncated():
    title = "a " * 100
    result = slugify(title)
    assert len(result) <= 80

def test_consecutive_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"

def test_leading_trailing_hyphens_stripped():
    assert slugify("--hello--") == "hello"

def test_unicode_preserved():
    assert slugify("café latte") == "cafe-latte"

def test_empty_string():
    assert slugify("") == "untitled"
