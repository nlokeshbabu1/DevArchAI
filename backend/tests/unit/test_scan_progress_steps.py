"""Tests for authoritative scan progress step mapping."""

from app.services.scan_lifecycle import ScanLifecycleStage
from app.services.scan_progress_steps import (
    lifecycle_to_store_step_label,
    normalize_progress_step_name,
    progress_store_step_index,
    progress_store_step_labels,
)


def test_progress_store_has_five_ordered_labels():
    labels = progress_store_step_labels()
    assert len(labels) == 5
    assert labels[0] == "Connect to repository"
    assert labels[-1] == "Analyze findings"


def test_lifecycle_ids_map_to_labels():
    assert normalize_progress_step_name("connecting_repository") == "Connect to repository"
    assert normalize_progress_step_name("scanning") == "Security scan"
    assert lifecycle_to_store_step_label(ScanLifecycleStage.CLONED) == "Clone repository"


def test_step_index_matches_labels():
    for idx, label in enumerate(progress_store_step_labels()):
        assert progress_store_step_index(label) == idx


def test_unknown_step_returns_none():
    assert normalize_progress_step_name("bogus") is None
