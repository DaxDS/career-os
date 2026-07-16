from abc import ABC, abstractmethod
from typing import Any

from app.infrastructure.db.models import JobSource


class JobSearchPort(ABC):
    @abstractmethod
    def search(self, source: JobSource) -> list[dict[str, Any]]: ...
