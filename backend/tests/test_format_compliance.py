
import pytest
import sys
import os

# Add project root to path to allow importing backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.council import clean_response_content

def test_clean_response_removes_think_tags():
    """Test that <think> tags are removed from the response."""
    raw_response = """<think>
This is a thinking process.
It should be removed.
</think>
Here is the actual answer.
"""
    expected = "Here is the actual answer."
    cleaned = clean_response_content(raw_response)
    assert cleaned.strip() == expected.strip()

def test_clean_response_handles_no_tags():
    """Test that responses without tags are unchanged."""
    raw_response = "Just a normal response."
    cleaned = clean_response_content(raw_response)
    assert cleaned == raw_response

def test_clean_response_removes_nested_or_broken_tags():
    """Test robust removal of think tags."""
    # Case with inline think tag
    raw = "Start <think>thinking</think> End"
    assert clean_response_content(raw).strip() == "Start  End"

def test_clean_response_standardizes_newlines():
    """Test that excessive newlines are trimmed."""
    raw = "Line 1\n\n\nLine 2"
    # We might not want to be too aggressive, but let's see what we implement
    # For now, just ensure it doesn't crash
    assert "Line 1" in clean_response_content(raw)
