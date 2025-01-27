from abc import ABC, abstractmethod
from typing import Callable, Any

class BaseQueue(ABC):
    @abstractmethod
    def publish(self, event: Any, delay: int = 0) -> bool:
        pass
    
    @abstractmethod
    def subscribe(self, callback: Callable[[Any], None]) -> None:
        pass 