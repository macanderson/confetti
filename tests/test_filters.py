"""Unit tests for the filters module."""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from confetti.core.filters import (
    Filter,
    filter_hierarchical,
    iter_hierarchical,
    should_include_key,
)


class TestFilter:
    """Test suite for Filter class."""
    
    def test_init_empty(self):
        """Test Filter initialization with no arguments."""
        f = Filter()
        assert f.include_regex is None
        assert f.hierarchical_spec is None
        assert f.depth is None
        
    def test_init_with_regex(self):
        """Test Filter initialization with regex."""
        pattern = re.compile(r"^test_.*")
        f = Filter(include_regex=pattern)
        assert f.include_regex == pattern
        
    def test_from_dict_none(self):
        """Test from_dict with None."""
        assert Filter.from_dict(None) is None
        
    def test_from_dict_empty(self):
        """Test from_dict with empty dict."""
        assert Filter.from_dict({}) is None
        
    def test_from_dict_with_regex(self):
        """Test from_dict with regex string."""
        f = Filter.from_dict({"include_regex": r"^test_.*"})
        assert f is not None
        assert f.include_regex is not None
        assert f.include_regex.pattern == r"^test_.*"
        
    def test_from_dict_with_hierarchical(self):
        """Test from_dict with hierarchical spec."""
        spec = {"database": {"host": True, "port": True}}
        f = Filter.from_dict({"hierarchical_spec": spec})
        assert f is not None
        assert f.hierarchical_spec == spec
        
    def test_from_dict_with_depth(self):
        """Test from_dict with depth."""
        f = Filter.from_dict({"depth": 2})
        assert f is not None
        assert f.depth == 2
        
    def test_from_dict_with_all_fields(self):
        """Test from_dict with all fields."""
        f = Filter.from_dict({
            "include_regex": r"^test_.*",
            "hierarchical_spec": {"key": True},
            "depth": 3
        })
        assert f is not None
        assert f.include_regex is not None
        assert f.hierarchical_spec == {"key": True}
        assert f.depth == 3
        
    def test_from_dict_invalid_regex_type(self):
        """Test from_dict with non-string regex."""
        f = Filter.from_dict({"include_regex": 123})
        assert f is not None
        assert f.include_regex is None  # Invalid type ignored
        
    def test_frozen_dataclass(self):
        """Test that Filter is immutable."""
        f = Filter()
        with pytest.raises(AttributeError):
            f.depth = 5


class TestShouldIncludeKey:
    """Test suite for should_include_key function."""
    
    def test_no_filter(self):
        """Test that all keys are included with no filter."""
        assert should_include_key("any_key", None) is True
        assert should_include_key("", None) is True
        
    def test_filter_without_regex(self):
        """Test filter without regex includes all."""
        f = Filter(hierarchical_spec={"key": True})
        assert should_include_key("any_key", f) is True
        
    def test_filter_with_matching_regex(self):
        """Test filter with matching regex."""
        f = Filter(include_regex=re.compile(r"^test_.*"))
        assert should_include_key("test_key", f) is True
        assert should_include_key("test_another", f) is True
        
    def test_filter_with_non_matching_regex(self):
        """Test filter with non-matching regex."""
        f = Filter(include_regex=re.compile(r"^test_.*"))
        assert should_include_key("other_key", f) is False
        assert should_include_key("key_test", f) is False
        
    def test_filter_regex_search_not_match(self):
        """Test that regex uses search not match."""
        f = Filter(include_regex=re.compile(r"test"))
        assert should_include_key("my_test_key", f) is True
        assert should_include_key("testing", f) is True
        assert should_include_key("other", f) is False


class TestIterHierarchical:
    """Test suite for iter_hierarchical function."""
    
    def test_empty_dict(self):
        """Test with empty dictionary."""
        result = list(iter_hierarchical({}))
        assert result == []
        
    def test_flat_dict(self):
        """Test with flat dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        result = list(iter_hierarchical(data))
        assert sorted(result) == [
            ("key1", "value1"),
            ("key2", "value2")
        ]
        
    def test_nested_dict(self):
        """Test with nested dictionary."""
        data = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "cache": "redis"
        }
        result = list(iter_hierarchical(data))
        assert sorted(result) == [
            ("cache", "redis"),
            ("database.host", "localhost"),
            ("database.port", 5432)
        ]
        
    def test_deeply_nested(self):
        """Test with deeply nested dictionary."""
        data = {
            "a": {
                "b": {
                    "c": {
                        "d": "value"
                    }
                }
            }
        }
        result = list(iter_hierarchical(data))
        assert result == [("a.b.c.d", "value")]
        
    def test_with_list_values(self):
        """Test that lists are emitted as-is."""
        data = {
            "items": ["a", "b", "c"],
            "nested": {
                "list": [1, 2, 3]
            }
        }
        result = list(iter_hierarchical(data))
        assert sorted(result) == [
            ("items", ["a", "b", "c"]),
            ("nested.list", [1, 2, 3])
        ]
        
    def test_with_parent_prefix(self):
        """Test with parent prefix."""
        data = {"key": "value"}
        result = list(iter_hierarchical(data, parent="prefix"))
        assert result == [("prefix.key", "value")]
        
    def test_depth_limit_zero(self):
        """Test with depth limit of 0."""
        data = {
            "key": "value",
            "nested": {"inner": "value"}
        }
        result = list(iter_hierarchical(data, depth=0))
        assert sorted(result) == [
            ("key", "value"),
            ("nested", {"inner": "value"})
        ]
        
    def test_depth_limit_one(self):
        """Test with depth limit of 1."""
        data = {
            "a": {
                "b": {
                    "c": "value"
                }
            }
        }
        result = list(iter_hierarchical(data, depth=1))
        assert result == [("a.b", {"c": "value"})]
        
    def test_depth_limit_negative(self):
        """Test with negative depth (should return nothing)."""
        data = {"key": "value"}
        result = list(iter_hierarchical(data, depth=-1))
        assert result == []
        
    def test_mixed_types(self):
        """Test with mixed value types."""
        data = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "dict": {"nested": "value"},
            "list": [1, 2]
        }
        result = dict(iter_hierarchical(data))
        assert result["string"] == "text"
        assert result["number"] == 42
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["none"] is None
        assert result["dict.nested"] == "value"
        assert result["list"] == [1, 2]


class TestFilterHierarchical:
    """Test suite for filter_hierarchical function."""
    
    def test_no_spec_no_depth(self):
        """Test with no spec and no depth limit."""
        data = {
            "a": {"b": "value"},
            "c": "other"
        }
        result = filter_hierarchical(data, None, None)
        assert result == {
            "a.b": "value",
            "c": "other"
        }
        
    def test_no_spec_with_depth(self):
        """Test with no spec but with depth limit."""
        data = {
            "a": {
                "b": {
                    "c": "deep"
                }
            }
        }
        result = filter_hierarchical(data, None, 1)
        assert result == {"a.b": {"c": "deep"}}
        
    def test_with_spec_simple(self):
        """Test with simple spec."""
        data = {
            "include": "yes",
            "exclude": "no"
        }
        spec = {"include": True}
        result = filter_hierarchical(data, spec, None)
        assert result == {"include": "yes"}
        
    def test_with_spec_nested(self):
        """Test with nested spec."""
        data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "password": "secret"
            },
            "cache": "redis"
        }
        spec = {
            "database": {
                "host": True,
                "port": True
            }
        }
        result = filter_hierarchical(data, spec, None)
        assert result == {
            "database.host": "localhost",
            "database.port": 5432
        }
        
    def test_with_spec_partial_path(self):
        """Test spec with partial path match."""
        data = {
            "a": {
                "b": {
                    "c": "value",
                    "d": "other"
                }
            }
        }
        spec = {"a": {"b": True}}
        result = filter_hierarchical(data, spec, None)
        assert result == {
            "a.b.c": "value",
            "a.b.d": "other"
        }
        
    def test_with_spec_and_depth(self):
        """Test with both spec and depth."""
        data = {
            "a": {
                "b": {
                    "c": {
                        "d": "deep"
                    }
                }
            },
            "x": "value"
        }
        spec = {"a": True}
        result = filter_hierarchical(data, spec, 2)
        assert result == {"a.b.c": {"d": "deep"}}
        
    def test_spec_with_false_values(self):
        """Test that spec with False values excludes keys."""
        data = {
            "include": "yes",
            "exclude": "no"
        }
        spec = {"include": True, "exclude": False}
        result = filter_hierarchical(data, spec, None)
        assert result == {"include": "yes"}
        
    def test_empty_data(self):
        """Test with empty data."""
        result = filter_hierarchical({}, {"key": True}, None)
        assert result == {}
        
    def test_empty_spec(self):
        """Test with empty spec (excludes all)."""
        data = {"key": "value"}
        result = filter_hierarchical(data, {}, None)
        assert result == {}