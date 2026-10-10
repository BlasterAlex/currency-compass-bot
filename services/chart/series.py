from __future__ import annotations

from dataclasses import dataclass

from clients.cbr import CbrSeriesPoint


@dataclass(frozen=True, slots=True)
class SeriesExtremes:
    peak: CbrSeriesPoint
    trough: CbrSeriesPoint
    last: CbrSeriesPoint
    flat: bool


def analyze_series(points: list[CbrSeriesPoint]) -> SeriesExtremes | None:
    """Pick peak/trough of the CBR nominal quote (latest on ties). Empty → None."""
    if not points:
        return None

    peak = points[0]
    trough = points[0]
    for point in points[1:]:
        if point.value > peak.value or (
            point.value == peak.value and point.date >= peak.date
        ):
            peak = point
        if point.value < trough.value or (
            point.value == trough.value and point.date >= trough.date
        ):
            trough = point

    last = points[-1]
    return SeriesExtremes(
        peak=peak,
        trough=trough,
        last=last,
        flat=peak.value == trough.value,
    )
