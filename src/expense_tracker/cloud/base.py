from abc import ABC, abstractmethod


class CloudStorageProvider(ABC):
    @abstractmethod
    def upload(self, key: str, data: str) -> None:
        """Upload a JSON string to the given key."""

    @abstractmethod
    def download(self, key: str) -> str | None:
        """Download the content at key. Returns None if not found."""
