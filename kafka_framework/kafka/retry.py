"""
Retry mechanism implementation.
"""
from typing import Any, Callable, List, Optional, Type, Union
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: Optional[List[Type[Exception]]] = None,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions or [Exception]
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)
        
    def should_retry(self, exception: Exception) -> bool:
        """Check if an exception should trigger a retry."""
        return any(isinstance(exception, exc) for exc in self.exceptions)

class RetryHandler:
    """Handles retry logic for message processing."""
    def __init__(self, config: RetryConfig):
        self.config = config
        
    async def execute_with_retry(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if not self.config.should_retry(e):
                    raise
                    
                if attempt == self.config.max_attempts:
                    logger.error(
                        f"All retry attempts failed for {func.__name__}. "
                        f"Last error: {str(e)}"
                    )
                    raise
                    
                delay = self.config.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt} failed for {func.__name__}. "
                    f"Retrying in {delay} seconds. Error: {str(e)}"
                )
                await asyncio.sleep(delay)
                
        # This should never be reached due to the raise in the loop
        raise last_exception
