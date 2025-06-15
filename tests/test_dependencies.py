"""
Unit tests for dependency injection system.
"""

import pytest

from kafka_framework.dependencies.injection import (
    Dependant,
    DependencyCache,
    Depends,
    get_dependant,
    solve_dependencies,
)


def test_depends_not_callable():
    """Test that Depends is not directly callable."""
    dep = Depends(lambda: None)
    with pytest.raises(RuntimeError):
        dep()


def test_dependency_cache():
    """Test DependencyCache operations."""
    cache = DependencyCache()

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test get non-existent key
    assert cache.get("non_existent") is None

    # Test clear
    cache.clear()
    assert cache.get("key1") is None


def test_get_dependant_no_deps():
    """Test get_dependant with no dependencies."""

    def func():
        return "test"

    dependant = get_dependant(func)
    assert isinstance(dependant, Dependant)
    assert dependant.call == func
    assert len(dependant.dependencies) == 0


def test_get_dependant_with_deps():
    """Test get_dependant with dependencies."""

    def dep1():
        return "dep1"

    def dep2():
        return "dep2"

    def func(d1=Depends(dep1), d2=Depends(dep2)):
        return f"{d1}_{d2}"

    dependant = get_dependant(func)
    assert len(dependant.dependencies) == 2
    assert all(isinstance(d, Dependant) for d in dependant.dependencies)
    assert dependant.dependencies[0].call == dep1
    assert dependant.dependencies[1].call == dep2


def test_get_dependant_nested():
    """Test get_dependant with nested dependencies."""

    def dep_inner():
        return "inner"

    def dep_outer(inner=Depends(dep_inner)):
        return f"outer_{inner}"

    def func(outer=Depends(dep_outer)):
        return f"func_{outer}"

    dependant = get_dependant(func)
    assert len(dependant.dependencies) == 1
    outer_dep = dependant.dependencies[0]
    assert len(outer_dep.dependencies) == 1
    assert outer_dep.dependencies[0].call == dep_inner


@pytest.mark.asyncio
async def test_solve_dependencies_sync():
    """Test solving synchronous dependencies."""

    def dep1():
        return "dep1"

    def dep2():
        return "dep2"

    def func(d1=Depends(dep1), d2=Depends(dep2)):
        return f"{d1}_{d2}"

    dependant = get_dependant(func)
    values = await solve_dependencies(dependant)

    # Call the function with resolved values
    result = func(**values)
    assert result == "dep1_dep2"


@pytest.mark.asyncio
async def test_solve_dependencies_async():
    """Test solving asynchronous dependencies."""

    async def async_dep():
        return "async"

    def sync_dep():
        return "sync"

    async def func(a=Depends(async_dep), s=Depends(sync_dep)):
        return f"{a}_{s}"

    dependant = get_dependant(func)
    values = await solve_dependencies(dependant)

    # Call the function with resolved values
    result = await func(**values)
    assert result == "async_sync"


@pytest.mark.asyncio
async def test_solve_dependencies_with_cache():
    """Test dependency caching."""
    call_count = 0

    def counted_dep():
        nonlocal call_count
        call_count += 1
        return "value"

    def func1(d=Depends(counted_dep)):
        return d

    def func2(d=Depends(counted_dep)):
        return d

    cache = DependencyCache()

    # Solve dependencies for both functions using same cache
    dep1 = get_dependant(func1)
    dep2 = get_dependant(func2)

    values1 = await solve_dependencies(dep1, cache)
    values2 = await solve_dependencies(dep2, cache)

    # Should only be called once due to caching
    assert call_count == 1
    assert func1(**values1) == "value"
    assert func2(**values2) == "value"


@pytest.mark.asyncio
async def test_solve_dependencies_no_cache():
    """Test dependencies without caching."""
    call_count = 0

    def counted_dep():
        nonlocal call_count
        call_count += 1
        return "value"

    def func1(d=Depends(counted_dep, use_cache=False)):
        return d

    def func2(d=Depends(counted_dep, use_cache=False)):
        return d

    cache = DependencyCache()

    # Solve dependencies for both functions
    dep1 = get_dependant(func1)
    dep2 = get_dependant(func2)

    values1 = await solve_dependencies(dep1, cache)
    values2 = await solve_dependencies(dep2, cache)

    # Should be called twice since caching is disabled
    assert call_count == 2
    assert func1(**values1) == "value"
    assert func2(**values2) == "value"


@pytest.mark.asyncio
async def test_complex_dependency_tree():
    """Test complex dependency tree with mixed sync/async and caching."""
    calls = []

    async def async_leaf():
        calls.append("async_leaf")
        return "async"

    def sync_leaf():
        calls.append("sync_leaf")
        return "sync"

    def mid_level(l1=Depends(async_leaf), l2=Depends(sync_leaf)):
        calls.append("mid_level")
        return f"mid_{l1}_{l2}"

    async def top_level(m=Depends(mid_level), l1=Depends(async_leaf), l2=Depends(sync_leaf)):
        calls.append("top_level")
        return f"top_{m}_{l1}_{l2}"

    dependant = get_dependant(top_level)
    values = await solve_dependencies(dependant)
    result = await top_level(**values)

    # Verify execution order and caching
    assert len(calls) == 4  # Each dependency should be called exactly once
    assert "async_leaf" in calls
    assert "sync_leaf" in calls
    assert "mid_level" in calls
    assert "top_level" in calls

    # Verify final result combines all dependencies correctly
    assert result == "top_mid_async_sync_async_sync"
