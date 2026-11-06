#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caching and API counting utilities.

This module provides file-based caching for CloudWatch data
and tracking of API request counts.
"""

import fcntl
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger("cache")


class DataCache:
    """File-based cache for CloudWatch data.

    Caches data to JSON files with TTL-based expiration.
    """

    def __init__(self, cache_dir: Path | str, ttl: int, prefix: str = "") -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds
            prefix: Optional prefix for cache file names (e.g., "discovery_", "metrics_")
        """
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl
        self._prefix = prefix
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get the file path for a cache key.

        Sanitizes the key to prevent path traversal attacks.

        Args:
            key: Cache key (e.g., service name)

        Returns:
            Safe path within the cache directory

        Raises:
            ValueError: If the key would result in a path outside cache_dir
        """
        # Sanitize key: only allow alphanumeric, underscore, and hyphen
        safe_key = "".join(c if c.isalnum() or c in "_-" else "_" for c in key)
        filename = f"{self._prefix}{safe_key}.json" if self._prefix else f"{safe_key}.json"
        path = (self._cache_dir / filename).resolve()

        # Security check: ensure path is within cache directory
        if not path.is_relative_to(self._cache_dir.resolve()):
            raise ValueError(f"Invalid cache key would escape cache directory: {key}")

        return path

    def load(
        self, key: str, config_key: str | None = None, ignore_ttl: bool = False
    ) -> dict[str, Any] | None:
        """Load cached data if valid.

        Uses file locking to prevent race conditions with concurrent access.
        TTL validation is based on timestamp stored in the cached data.
        Config key validation ensures cache is invalidated when configuration changes.

        Args:
            key: Cache key
            config_key: Optional configuration key to validate against cached data.
                        If provided and doesn't match, cache is considered invalid.
            ignore_ttl: Return the data regardless of its age (used while monitoring
                        is stopped, to keep the last known resources)

        Returns:
            Cached data dictionary or None if not valid/expired/config mismatch
        """
        try:
            path = self._get_path(key)
        except ValueError as err:
            logger.warning("Invalid cache key: %s", err)
            return None

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as file:
                # Acquire shared lock for reading (allows concurrent reads)
                fcntl.flock(file.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(file)
                finally:
                    fcntl.flock(file.fileno(), fcntl.LOCK_UN)

                # Validate TTL using stored timestamp
                cached_at = data.get("_cached_at", 0)
                if not ignore_ttl and time.time() - cached_at > self._ttl:
                    logger.debug("Cache expired for key '%s'", key)
                    return None

                # Validate config key if provided
                if config_key and data.get("_config_key") != config_key:
                    logger.debug(
                        "Config changed for '%s' (expected '%s', got '%s'), cache invalidated",
                        key,
                        config_key,
                        data.get("_config_key"),
                    )
                    return None

                return data
        except (json.JSONDecodeError, OSError) as err:
            logger.debug("Failed to load cache for '%s': %s", key, err)
            return None

    def save(self, key: str, data: dict[str, Any], config_key: str | None = None) -> None:
        """Save data to cache.

        Writes atomically (temp file + rename), so readers never see a partial file.
        Stores a timestamp for TTL validation on load.

        Args:
            key: Cache key
            data: Data to cache
            config_key: Optional configuration key to store with the cache.
                        Used for validation on load to detect config changes.
        """
        try:
            path = self._get_path(key)
        except ValueError as err:
            logger.warning("Invalid cache key, cannot save: %s", err)
            return

        # Add timestamp and config key for validation
        data_with_metadata = data.copy()
        data_with_metadata["_cached_at"] = time.time()
        if config_key:
            data_with_metadata["_config_key"] = config_key

        # Write to a temp file and rename it, so an aborted write (e.g. agent
        # killed on timeout) never leaves a truncated cache file behind
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(data_with_metadata, file)
            os.replace(tmp_path, path)
        except OSError as err:
            logger.warning("Failed to save cache for '%s': %s", key, err)
            tmp_path.unlink(missing_ok=True)

    def delete(self, key: str) -> None:
        """Delete a cache entry.

        Used to remove corrupted cache files.

        Args:
            key: Cache key to delete
        """
        try:
            path = self._get_path(key)
            path.unlink(missing_ok=True)
            logger.debug("Deleted cache for key '%s'", key)
        except (ValueError, OSError) as err:
            logger.debug("Could not delete cache for '%s': %s", key, err)


class APICounter:
    """Counter for tracking API requests.

    Used to monitor CloudWatch API usage against the Free Tier limit.
    Tracks both total requests and breakdown by service/API type.
    """

    def __init__(self) -> None:
        """Initialize the counter."""
        self._count = 0
        self._by_service: dict[str, dict[str, int]] = {}

    def increment(
        self, count: int = 1, service: str = "", api_type: str = "get_statistics"
    ) -> None:
        """Increment the request count.

        Args:
            count: Number of requests to add
            service: Service name for breakdown tracking (e.g., "ec2", "rds")
            api_type: API type ("list_metrics" or "get_statistics")
        """
        self._count += count
        if service:
            if service not in self._by_service:
                self._by_service[service] = {"list_metrics": 0, "get_statistics": 0}
            self._by_service[service][api_type] += count

    def add_counts(self, count: int, breakdown: dict[str, dict[str, int]]) -> None:
        """Merge counts from another counter into this counter.

        Used to merge per-service counters into the global counter after
        the parallel run has finished.

        Args:
            count: Total number of requests to add
            breakdown: Dict mapping service names to their API call counts
        """
        self._count += count
        for service, api_types in breakdown.items():
            if service not in self._by_service:
                self._by_service[service] = {"list_metrics": 0, "get_statistics": 0}
            for api_type, api_count in api_types.items():
                self._by_service[service][api_type] = (
                    self._by_service[service].get(api_type, 0) + api_count
                )

    def get_count(self) -> int:
        """Get the total request count."""
        return self._count

    def get_breakdown(self) -> dict[str, dict[str, int]]:
        """Get the breakdown of requests by service.

        Returns:
            Dictionary mapping service names to their API call counts
            Example: {"ec2": {"list_metrics": 1, "get_statistics": 5}, ...}
        """
        return self._by_service.copy()
