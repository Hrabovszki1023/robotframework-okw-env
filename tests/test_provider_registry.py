"""Tests for provider registry."""

import pytest

from okw_env.provider_registry import get_provider, discover_providers


def test_discover_providers_returns_dict():
    result = discover_providers()
    assert isinstance(result, dict)


def test_unknown_provider_raises():
    with pytest.raises(KeyError, match="not found"):
        get_provider("nonexistent_provider_xyz")
