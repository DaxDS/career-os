from abc import ABC, abstractmethod


class JobClassifierPort(ABC):
    @abstractmethod
    def classify(
        self,
        title: str,
        description: str,
        remote_type: str | None = None,
        *,
        company: str = "",
        location: str = "",
    ) -> dict: ...
