# app/strategies/__init__.py
import pkgutil
from importlib import import_module
from typing import Type
from abc import ABC, abstractmethod
from ..schemas import AddressResult

class GeocodingStrategy(ABC):
    """Abstract base class for all geocoding strategies"""
    @abstractmethod
    def geocode(self, address: str, country_code: str) -> list[AddressResult]:
        """Main geocoding interface to be implemented by all strategies"""
        pass

class StrategyFactory:
    """Registry for all available geocoding strategies"""
    _strategies: dict[str, Type[GeocodingStrategy]] = {}

    @classmethod
    def register(cls, name: str) -> callable:
        """Decorator for registering new strategies"""
        def decorator(strategy_class: Type[GeocodingStrategy]) -> Type[GeocodingStrategy]:
            cls._strategies[name.lower()] = strategy_class
            return strategy_class
        return decorator

    @classmethod
    def get_strategy(cls, name: str) -> GeocodingStrategy:
        """Retrieve a strategy implementation by name"""
        normalized_name = name.lower()

        if normalized_name not in cls._strategies:
            raise ValueError(
                f"Unsupported strategy: {name}. "
                f"Available strategies: {', '.join(cls._strategies.keys())}"
            )

        return cls._strategies[normalized_name]()

# Auto-discover and register all strategy implementations
__path__ = pkgutil.extend_path(__path__, __name__)
for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name != "__init__":  # Skip self
        import_module(f"{__name__}.{module_name}")

__all__ = ['GeocodingStrategy', 'StrategyFactory']
