"""从 benchmark CSV 生成 C2LAKE Figure 4 复现 PNG。"""

from __future__ import annotations

import argparse
import csv
import struct
import zlib
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

_PHASE_COLORS = {
    "Setup": (31, 119, 180),
    "SetSecretValue": (255, 127, 14),
    "PartialPrivateKeyExtract": (44, 160, 44),
    "full_handshake": (214, 39, 40),
    "initiator_total": (148, 103, 189),
    "responder_total": (140, 86, 75),
    "paper": (127, 127, 127),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--table-input",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/table7_reproduced.csv"),
    )
    parser.add_argument(
        "--comparison-input",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/table7_comparison.csv"),
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=Path("artifacts/figures/C2LAKE/figure4_reproduced.png"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    table_rows = _read_csv(args.table_input)
    comparison_rows = _read_csv(args.comparison_input)
    args.figure_output.parent.mkdir(parents=True, exist_ok=True)
    render_figure(table_rows, comparison_rows, args.figure_output)
    print(args.figure_output)
    return 0


def render_figure(
    table_rows: list[dict[str, str]],
    comparison_rows: list[dict[str, str]],
    output: Path,
) -> Path:
    width = 1200
    height = 900
    canvas = _new_canvas(width, height, (255, 255, 255))
    panels = (
        (40, 40, 520, 360),
        (640, 40, 520, 360),
        (40, 500, 520, 340),
        (640, 500, 520, 340),
    )
    _draw_panel(
        canvas,
        panels[0],
        _series_from_table(
            table_rows,
            family="paper_literal",
            phases=(
                "Setup",
                "SetSecretValue",
                "PartialPrivateKeyExtract",
                "full_handshake",
            ),
        ),
    )
    _draw_panel(
        canvas,
        panels[1],
        _series_from_table(
            table_rows,
            family="audited_prime",
            phases=(
                "Setup",
                "SetSecretValue",
                "PartialPrivateKeyExtract",
                "full_handshake",
            ),
        ),
    )
    _draw_panel(
        canvas,
        panels[2],
        _paper_vs_literal_series(comparison_rows),
    )
    _draw_panel(
        canvas,
        panels[3],
        _series_from_table(
            table_rows,
            family="paper_literal",
            phases=("initiator_total", "responder_total", "full_handshake"),
        ),
    )
    _draw_legend(canvas, x=40, y=850)
    _write_png(output, canvas)
    return output


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _series_from_table(
    rows: list[dict[str, str]],
    *,
    family: str,
    phases: tuple[str, ...],
) -> dict[str, list[tuple[int, float]]]:
    series: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        if row["family"] != family or row["phase"] not in phases or not row["mean_ms"]:
            continue
        series[row["phase"]].append((int(row["m"]), float(row["mean_ms"])))
    return {key: sorted(value) for key, value in series.items()}


def _paper_vs_literal_series(rows: list[dict[str, str]]) -> dict[str, list[tuple[int, float]]]:
    series: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        if (
            row.get("family") != "paper_literal"
            or row["phase"] != "Key_Agreement"
            or row["timing_boundary"] != "full_handshake"
        ):
            continue
        series["paper"].append((int(row["m"]), float(row["paper_ms"])))
        if row["reproduced_mean_ms"]:
            series["full_handshake"].append((int(row["m"]), float(row["reproduced_mean_ms"])))
    return {key: sorted(value) for key, value in series.items()}


def _draw_panel(
    canvas: list[list[tuple[int, int, int]]],
    panel: tuple[int, int, int, int],
    series: dict[str, list[tuple[int, float]]],
) -> None:
    x, y, width, height = panel
    _rect(canvas, x, y, width, height, (248, 248, 248))
    _line(canvas, x + 40, y + height - 35, x + width - 20, y + height - 35, (0, 0, 0))
    _line(canvas, x + 40, y + 20, x + 40, y + height - 35, (0, 0, 0))
    all_points = [point for points in series.values() for point in points]
    if not all_points:
        return
    min_m = min(point[0] for point in all_points)
    max_m = max(point[0] for point in all_points)
    max_ms = max(point[1] for point in all_points) or 1.0
    for name, points in series.items():
        color = _PHASE_COLORS.get(name, (0, 0, 0))
        scaled = [
            (
                _scale_x(m, min_m, max_m, x + 50, x + width - 30),
                _scale_y(ms, max_ms, y + 30, y + height - 45),
            )
            for m, ms in points
        ]
        for left, right in pairwise(scaled):
            _line(canvas, left[0], left[1], right[0], right[1], color)
        for px, py in scaled:
            _rect(canvas, px - 3, py - 3, 7, 7, color)


def _draw_legend(canvas: list[list[tuple[int, int, int]]], *, x: int, y: int) -> None:
    offset = 0
    for color in _PHASE_COLORS.values():
        _rect(canvas, x + offset, y, 32, 16, color)
        offset += 42


def _scale_x(value: int, minimum: int, maximum: int, left: int, right: int) -> int:
    if maximum == minimum:
        return (left + right) // 2
    return int(left + ((value - minimum) / (maximum - minimum)) * (right - left))


def _scale_y(value: float, maximum: float, top: int, bottom: int) -> int:
    return int(bottom - (value / maximum) * (bottom - top))


def _new_canvas(
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> list[list[tuple[int, int, int]]]:
    return [[color for _column in range(width)] for _row in range(height)]


def _rect(
    canvas: list[list[tuple[int, int, int]]],
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> None:
    max_y = min(len(canvas), y + height)
    max_x = min(len(canvas[0]), x + width)
    for row in range(max(0, y), max_y):
        for column in range(max(0, x), max_x):
            canvas[row][column] = color


def _line(
    canvas: list[list[tuple[int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    x = x0
    y = y0
    while True:
        if 0 <= y < len(canvas) and 0 <= x < len(canvas[0]):
            canvas[y][x] = color
        if x == x1 and y == y1:
            break
        doubled_error = 2 * error
        if doubled_error >= dy:
            error += dy
            x += sx
        if doubled_error <= dx:
            error += dx
            y += sy


def _write_png(path: Path, canvas: list[list[tuple[int, int, int]]]) -> None:
    height = len(canvas)
    width = len(canvas[0])
    raw = b"".join(b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in canvas)
    png = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw, level=9)),
            _chunk(b"IEND", b""),
        )
    )
    path.write_bytes(png)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack("!I", len(payload))
        + kind
        + payload
        + struct.pack("!I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


if __name__ == "__main__":
    raise SystemExit(main())
