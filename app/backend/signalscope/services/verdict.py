"""Turn a calibrated probability into responsible, plain-language wording."""

from signalscope.schemas.analysis import (
    BandThresholds,
    Provenance,
    SignalDirection,
    SignalSource,
    Verdict,
    VerdictBand,
)

DISCLAIMER = (
    "This is an automated likelihood assessment, not proof. Detectors can be wrong — especially on "
    "heavily edited, compressed or screenshotted images, and on output from newer generators. "
    "Do not use this result as the sole basis for an accusation."
)


def make_verdict(prob_ai: float, likely_real_max: float, likely_ai_min: float) -> Verdict:
    thresholds = BandThresholds(likely_real_max=likely_real_max, likely_ai_min=likely_ai_min)

    if prob_ai >= likely_ai_min:
        band, headline = VerdictBand.LIKELY_AI, "Likely AI-generated"
        summary = (
            "The image shows strong signs of AI generation."
            if prob_ai >= (1 + likely_ai_min) / 2
            else "The image shows several signs of AI generation, though not conclusively."
        )
    elif prob_ai <= likely_real_max:
        band, headline = VerdictBand.LIKELY_REAL, "Likely real"
        summary = (
            "We found few signs of AI generation."
            if prob_ai <= likely_real_max / 2
            else "We found only weak signs of AI generation. This does not rule it out."
        )
    else:
        band, headline = VerdictBand.UNCERTAIN, "Uncertain"
        summary = (
            "The signals are mixed, so we can't make a reliable call either way. "
            "Check the highlighted regions and provenance details, and seek other sources."
        )

    return Verdict(band=band, prob_ai=prob_ai, headline=headline, summary=summary, thresholds=thresholds)


# Only signed / standardised declarations are strong enough to compare against the model.
_STRONG_SOURCES = {SignalSource.C2PA, SignalSource.XMP, SignalSource.EMBEDDED_TEXT}


def assess_agreement(verdict: Verdict, provenance: Provenance) -> None:
    """Annotate `provenance` with whether metadata agrees with the visual verdict (mutates in place)."""
    strong = [
        s
        for s in provenance.signals
        if s.source in _STRONG_SOURCES and s.direction != SignalDirection.NEUTRAL
    ]
    if not strong:
        provenance.agreement = "no_evidence"
        provenance.agreement_note = None
        return

    says_ai = any(s.direction == SignalDirection.AI for s in strong)
    says_real = any(s.direction == SignalDirection.REAL for s in strong)
    if says_ai and says_real:
        provenance.agreement = "conflicts"
        provenance.agreement_note = "Metadata contains contradictory declarations — treat it with caution."
        return

    metadata_band = VerdictBand.LIKELY_AI if says_ai else VerdictBand.LIKELY_REAL
    metadata_label = "AI-generated" if says_ai else "a camera capture"
    if verdict.band == metadata_band:
        provenance.agreement = "agrees"
        provenance.agreement_note = (
            f"Metadata declares {metadata_label}, consistent with the visual analysis."
        )
    elif verdict.band == VerdictBand.UNCERTAIN:
        provenance.agreement = "model_uncertain"
        provenance.agreement_note = (
            f"The visual analysis is uncertain, but metadata declares {metadata_label}. "
            "Declared provenance is usually the more reliable signal when it is signed."
        )
    else:
        provenance.agreement = "conflicts"
        provenance.agreement_note = (
            f"Metadata declares {metadata_label}, but the visual analysis disagrees. "
            "Metadata can be copied between files; signed Content Credentials are harder to fake."
        )
