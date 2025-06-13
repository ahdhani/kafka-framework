"""
Dependency injection module for the Kafka framework.
"""
from .injection import Depends, Dependant, solve_dependencies, DependencyCache

__all__ = ["Depends", "Dependant", "solve_dependencies", "DependencyCache"]
