import re

import pytest

from signalscope.schemas.analysis import (
    C2PAInfo,
    ExifInfo,
    Provenance,
    ProvenanceSignal,
    SignalDirection,
    SignalSource,
    VerdictBand,
)
from signalscope.services.verdict import assess_agreement, make_verdict

REAL_MAX, AI_MIN = 0.35, 0.65


@pytest.mark.parametrize(
    ("prob", "band"),
    [
        (0.0, VerdictBand.LIKELY_REAL),
        (0.35, VerdictBand.LIKELY_REAL),
        (0.3501, VerdictBand.UNCERTAIN),
        (0.5, VerdictBand.UNCERTAIN),
        (0.6499, VerdictBand.UNCERTAIN),
        (0.65, VerdictBand.LIKELY_AI),
        (1.0, VerdictBand.LIKELY_AI),
    ],
)
def test_band_edges(prob, band):
    assert make_verdict(prob, REAL_MAX, AI_MIN).band == band


@pytest.mark.parametrize("prob", [0.0, 0.2, 0.5, 0.7, 0.99])
def test_wording_never_overclaims(prob):
    verdict = make_verdict(prob, REAL_MAX, AI_MIN)
    text = f"{verdict.headline} {verdict.summary}".lower()

    for banned in ("fake", "certain", "certainly", "definitely", "proof", "100%"):
        assert not re.search(rf"\b{re.escape(banned)}(?!\w)", text), banned


def _provenance(*signals: ProvenanceSignal) -> Provenance:
    return Provenance(
        exif=ExifInfo(present=False), c2pa=C2PAInfo(present=False, checked=True), signals=list(signals)
    )


AI_DECLARED = ProvenanceSignal(source=SignalSource.C2PA, direction=SignalDirection.AI, message="ai")
CAMERA_EXIF = ProvenanceSignal(source=SignalSource.EXIF, direction=SignalDirection.REAL, message="cam")


@pytest.mark.parametrize(
    ("prob", "signals", "expected"),
    [
        (0.9, [AI_DECLARED], "agrees"),
        (0.1, [AI_DECLARED], "conflicts"),
        (0.5, [AI_DECLARED], "model_uncertain"),
        (0.1, [CAMERA_EXIF], "no_evidence"),  # EXIF alone is too weak to compare against
        (0.9, [], "no_evidence"),
    ],
)
def test_agreement(prob, signals, expected):
    provenance = _provenance(*signals)

    assess_agreement(make_verdict(prob, REAL_MAX, AI_MIN), provenance)

    assert provenance.agreement == expected
    assert (provenance.agreement_note is None) == (expected == "no_evidence")
