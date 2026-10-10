from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.offsetbox import AnchoredOffsetbox, HPacker, OffsetImage, TextArea  # noqa: E402

from clients.cbr import CbrSeriesPoint
from services.chart.series import SeriesExtremes
from services.flags import currency_country
from services.rates import format_nominal

_FLAG_DIR = Path(__file__).resolve().parents[2] / "assets" / "flags"

plt.rcParams["font.family"] = "DejaVu Sans"


@dataclass(frozen=True, slots=True)
class ChartPanel:
    code: str
    name: str
    points: list[CbrSeriesPoint]
    extremes: SeriesExtremes


def _marker_entries(extremes: SeriesExtremes) -> list[tuple[CbrSeriesPoint, str, str, str]]:
    """One visual marker per distinct date; roles merge when points coincide."""
    roles: dict[date, list[str]] = {}
    points_by_date: dict[date, CbrSeriesPoint] = {}
    for point, role in (
        (extremes.peak, "макс."),
        (extremes.trough, "мин."),
    ):
        roles.setdefault(point.date, [])
        if role not in roles[point.date]:
            roles[point.date].append(role)
        points_by_date[point.date] = point

    style = {
        "макс.": ("o", "#c0392b"),
        "мин.": ("o", "#27ae60"),
    }
    entries: list[tuple[CbrSeriesPoint, str, str, str]] = []
    for day, point in sorted(points_by_date.items()):
        label = "/".join(roles[day])
        primary = roles[day][0]
        marker, color = style[primary]
        entries.append((point, marker, color, label))
    return entries


_SAMPLES_PER_SEGMENT = 8


def _pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Fritsch-Carlson slopes: the curve stays inside each segment's min and max."""
    h = np.diff(x)
    delta = np.diff(y) / h
    n = len(y)
    slopes = np.zeros(n)
    if n == 2:
        slopes[:] = delta[0]
        return slopes

    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0:
            slopes[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            slopes[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])

    slopes[0] = ((2 * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / (h[0] + h[1])
    slopes[-1] = ((2 * h[-1] + h[-2]) * delta[-1] - h[-1] * delta[-2]) / (h[-1] + h[-2])
    for end, step in ((0, delta[0]), (-1, delta[-1])):
        if slopes[end] * step <= 0:
            slopes[end] = 0.0
        elif abs(slopes[end]) > abs(3 * step):
            slopes[end] = 3 * step
    return slopes


def smooth_series(
    dates: list[date], values: list[float]
) -> tuple[list[datetime], list[float]]:
    """Round the polyline through the real points. Fewer than 3 points stay as-is."""
    xs = [datetime.combine(day, datetime.min.time()) for day in dates]
    if len(dates) < 3:
        return xs, values

    x = np.array([day.toordinal() for day in dates], dtype=float)
    y = np.array(values, dtype=float)
    if np.any(np.diff(x) <= 0):
        return xs, values

    slopes = _pchip_slopes(x, y)
    out_x: list[datetime] = []
    out_y: list[float] = []
    for i in range(len(x) - 1):
        h = x[i + 1] - x[i]
        samples = _SAMPLES_PER_SEGMENT if i < len(x) - 2 else _SAMPLES_PER_SEGMENT + 1
        for step in range(samples):
            t = step / _SAMPLES_PER_SEGMENT
            h00 = (2 * t**3) - (3 * t**2) + 1
            h10 = t**3 - (2 * t**2) + t
            h01 = (-2 * t**3) + (3 * t**2)
            h11 = t**3 - t**2
            value = h00 * y[i] + h10 * h * slopes[i] + h01 * y[i + 1] + h11 * h * slopes[i + 1]
            out_x.append(datetime.fromordinal(int(x[i])) + timedelta(days=float(t * h)))
            out_y.append(float(value))
    return out_x, out_y


def _set_figure_title(fig: plt.Figure, period_label: str, date_from: date, date_to: date) -> None:
    """Title as before; only the dates inside the parentheses are bold."""
    start = date_from.strftime("%d.%m.%Y")
    end = date_to.strftime("%d.%m.%Y")
    prefix = f"Курсы ЦБ: {period_label} ("
    dates = f"{start} - {end}"
    suffix = ")"
    ghost = fig.suptitle(prefix + dates + suffix, fontsize=13)
    ghost.set_alpha(0)
    regular = {"size": 13, "weight": "regular"}
    bold = {"size": 13, "weight": "bold"}
    box = HPacker(
        children=[
            TextArea(prefix, textprops=regular),
            TextArea(dates, textprops=bold),
            TextArea(suffix, textprops=regular),
        ],
        align="baseline",
        pad=0,
        sep=0,
    )
    fig.add_artist(
        AnchoredOffsetbox(
            loc="upper center",
            child=box,
            pad=0,
            borderpad=0.35,
            frameon=False,
            bbox_to_anchor=(0.5, 1),
            bbox_transform=fig.transFigure,
        )
    )


class _RaisedFlag(OffsetImage):
    """Flag image shifted up by one pixel so it lines up with the title text."""

    def get_window_extent(self, renderer=None):
        return super().get_window_extent(renderer).translated(0, 1)


def _flag_image(code: str) -> OffsetImage | None:
    country = currency_country(code).lower()
    path = _FLAG_DIR / f"{country}.png"
    if not country or not path.is_file():
        return None
    return _RaisedFlag(mpimg.imread(path), zoom=0.33)


def _set_panel_title(ax: plt.Axes, code: str, name: str, nominal: str) -> None:
    label = f"{code} - {name} (за {nominal})"
    ax.set_title(label, loc="left", fontsize=10, color="none")
    bold = {"size": 10, "weight": "bold"}
    regular = {"size": 10, "weight": "regular"}
    text = HPacker(
        children=[
            TextArea(code, textprops=bold),
            TextArea(f" - {name} (за {nominal})", textprops=regular),
        ],
        align="baseline",
        pad=0,
        sep=0,
    )
    children: list = [text]
    flag = _flag_image(code)
    if flag is not None:
        children.insert(0, flag)
    box = HPacker(
        children=children,
        align="center",
        pad=0,
        sep=3,
    )
    ax.add_artist(
        AnchoredOffsetbox(
            loc="lower left",
            child=box,
            pad=0,
            borderpad=0,
            frameon=False,
            bbox_to_anchor=(0, 1.02),
            bbox_transform=ax.transAxes,
        )
    )


def render_chart_png(
    panels: list[ChartPanel],
    *,
    period_label: str,
    date_from: date,
    date_to: date,
) -> bytes:
    if not panels:
        raise ValueError("panels must not be empty")

    n = len(panels)
    fig, axes = plt.subplots(
        nrows=n,
        ncols=1,
        sharex=True,
        figsize=(10, max(2.8 * n, 3.0)),
        constrained_layout=True,
    )
    if n == 1:
        axes = [axes]

    _set_figure_title(fig, period_label, date_from, date_to)

    for ax, panel in zip(axes, panels, strict=True):
        xs = [p.date for p in panel.points]
        ys = [float(p.value) for p in panel.points]
        line_x, line_y = smooth_series(xs, ys)
        nominal = format_nominal(panel.points[-1].nominal)
        ax.plot(line_x, line_y, color="#1f4e79", linewidth=1.8)
        _set_panel_title(ax, panel.code, panel.name, nominal)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", labelrotation=30)

        for point, marker, color, label in _marker_entries(panel.extremes):
            ax.scatter(
                [point.date],
                [float(point.value)],
                marker=marker,
                color=color,
                zorder=5,
                label=label,
            )
        ax.legend(loc="upper left", fontsize=8, frameon=False)

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()
