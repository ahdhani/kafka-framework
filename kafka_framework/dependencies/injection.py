"""
Dependency injection system inspired by FastAPI.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Dependant:
    """
    Represents a dependency and its sub-dependencies.
    """

    call: Callable
    dependencies: list["Dependant"] = field(default_factory=list)
    cache_key: str | None = None


class Depends:
    """
    Declare dependencies to be injected.
    Similar to FastAPI's Depends.
    """

    def __init__(
        self,
        dependency: Callable,
        *,
        use_cache: bool = True,
    ):
        self.dependency = dependency
        self.use_cache = use_cache

    def __call__(self) -> Any:
        """
        This is not meant to be called directly.
        It will be called by the dependency injection system.
        """
        raise RuntimeError(
            "Depends is not callable directly. It should be used as a dependency marker."
        )


def get_dependant(call: Callable) -> Dependant:
    """
    Get dependencies for a callable.
    """
    signature = inspect.signature(call)
    dependant = Dependant(call=call)

    for _param_name, param in signature.parameters.items():
        if isinstance(param.default, Depends):
            sub_dependant = get_dependant(param.default.dependency)
            if param.default.use_cache:
                sub_dependant.cache_key = str(id(param.default.dependency))
            dependant.dependencies.append(sub_dependant)

    return dependant


class DependencyCache:
    """
    Cache for dependency values.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        """Get a cached value."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a cached value."""
        self._cache[key] = value

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()


async def solve_dependencies(
    dependant: Dependant,
    cache: DependencyCache | None = None,
) -> dict[str, Any]:
    """
    Solve dependencies for a dependant.
    Returns a dictionary of parameter values.
    """
    if cache is None:
        cache = DependencyCache()

    values: dict[str, Any] = {}
    signature = inspect.signature(dependant.call)

    # First solve sub-dependencies
    for sub_dependant in dependant.dependencies:
        if sub_dependant.cache_key and cache:
            cached_value = cache.get(sub_dependant.cache_key)
            if cached_value is not None:
                # Find parameter that uses this dependency
                for param_name, param in signature.parameters.items():
                    if (
                        isinstance(param.default, Depends)
                        and param.default.dependency == sub_dependant.call
                    ):
                        values[param_name] = cached_value
                        break
                continue

        sub_values = await solve_dependencies(sub_dependant, cache)

        # Call dependency function - handle both async and sync functions
        if inspect.iscoroutinefunction(sub_dependant.call):
            result = await sub_dependant.call(**sub_values)
        else:
            result = sub_dependant.call(**sub_values)

        if sub_dependant.cache_key and cache:
            cache.set(sub_dependant.cache_key, result)

        # Find parameter that uses this dependency
        for param_name, param in signature.parameters.items():
            if (
                isinstance(param.default, Depends)
                and param.default.dependency == sub_dependant.call
            ):
                values[param_name] = result
                break

    return values
