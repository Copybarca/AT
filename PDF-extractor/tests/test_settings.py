import pytest
from pydantic import ValidationError

from pdf_extractor.settings import (
    FragmentationSettings,
    RuntimeFragmentationSettings,
    ServiceSettings,
)


@pytest.mark.parametrize(
    ("minimum", "maximum", "tolerance"),
    [(0, 10, 2), (6, 5, 2), (5, 10, -1)],
)
def test_fragmentation_settings_reject_invalid_ranges(
    minimum: int,
    maximum: int,
    tolerance: int,
) -> None:
    with pytest.raises(ValidationError):
        FragmentationSettings(
            min_sentences=minimum,
            max_sentences=maximum,
            boundary_tolerance_sentences=tolerance,
        )


def test_runtime_replacement_does_not_mutate_existing_job_snapshot() -> None:
    initial = FragmentationSettings(
        min_sentences=5,
        max_sentences=10,
        boundary_tolerance_sentences=2,
    )
    provider = RuntimeFragmentationSettings(initial)

    accepted_job_snapshot = provider.snapshot()
    replacement = FragmentationSettings(
        min_sentences=3,
        max_sentences=7,
        boundary_tolerance_sentences=1,
    )
    provider.replace(replacement)

    assert accepted_job_snapshot == initial
    assert provider.snapshot() == replacement


def test_service_settings_load_fragmentation_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRAGMENT_MIN_SENTENCES", "4")
    monkeypatch.setenv("FRAGMENT_MAX_SENTENCES", "8")
    monkeypatch.setenv("FRAGMENT_BOUNDARY_TOLERANCE_SENTENCES", "3")

    settings = ServiceSettings(_env_file=None)

    assert settings.fragmentation == FragmentationSettings(
        min_sentences=4,
        max_sentences=8,
        boundary_tolerance_sentences=3,
    )
