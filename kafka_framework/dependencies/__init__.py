"""
Dependency injection module for the Kafka framework.
"""

from .injection import Dependant, DependencyCache, Depends, get_dependant, solve_dependencies

__all__ = ["Depends", "Dependant", "solve_dependencies", "DependencyCache", "get_dependant"]
