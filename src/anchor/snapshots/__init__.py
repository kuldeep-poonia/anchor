"""Snapshot and rollback manager for preserving workspace states."""

from anchor.snapshots.manager import SnapshotError, SnapshotManager, SnapshotManifest

__all__ = ["SnapshotError", "SnapshotManager", "SnapshotManifest"]
