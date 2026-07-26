"""无第三方绘图库依赖的审计图 PNG 渲染器。"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path

Color = tuple[int, int, int]
Point = tuple[float, float]

_PALETTE: tuple[Color, ...] = (
    (31, 119, 180),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
    (140, 86, 75),
    (227, 119, 194),
    (127, 127, 127),
)


def render_line_panels(
    panels: Sequence[Mapping[str, Sequence[Point]]],
    output: Path,
    *,
    width: int = 1200,
    panel_height: int = 360,
) -> Path:
    """把一组 CSV-derived line series 绘成 PNG panel。"""

    if not panels:
        raise ValueError("至少需要一个 panel")
    height = len(panels) * panel_height + 60
    canvas = _new_canvas(width, height, (255, 255, 255))
    for index, series in enumerate(panels):
        _draw_panel(
            canvas,
            (40, 30 + index * panel_height, width - 80, panel_height - 40),
            series,
        )
    _draw_legend(canvas, x=40, y=height - 24)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_png(output, canvas)
    return output


def _draw_panel(
    canvas: list[list[Color]],
    panel: tuple[int, int, int, int],
    series: Mapping[str, Sequence[Point]],
) -> None:
    x, y, width, height = panel
    _rect(canvas, x, y, width, height, (248, 248, 248))
    left, right = x + 48, x + width - 24
    top, bottom = y + 22, y + height - 38
    _line(canvas, left, bottom, right, bottom, (0, 0, 0))
    _line(canvas, left, top, left, bottom, (0, 0, 0))
    points = [point for values in series.values() for point in values]
    if not points:
        return
    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(0.0, min(point[1] for point in points))
    maximum_y = max(point[1] for point in points)
    if maximum_y == minimum_y:
        maximum_y = minimum_y + 1.0
    for series_index, (_name, raw_points) in enumerate(sorted(series.items())):
        color = _PALETTE[series_index % len(_PALETTE)]
        scaled = [
            (
                _scale(value_x, minimum_x, maximum_x, left, right),
                _scale(value_y, minimum_y, maximum_y, bottom, top),
            )
            for value_x, value_y in sorted(raw_points)
        ]
        for start, end in pairwise(scaled):
            _line(canvas, start[0], start[1], end[0], end[1], color)
        for point_x, point_y in scaled:
            _rect(canvas, point_x - 3, point_y - 3, 7, 7, color)


def _draw_legend(canvas: list[list[Color]], *, x: int, y: int) -> None:
    for index, color in enumerate(_PALETTE):
        _rect(canvas, x + index * 44, y, 32, 14, color)


def _scale(value: float, minimum: float, maximum: float, low: int, high: int) -> int:
    if maximum == minimum:
        return (low + high) // 2
    return int(low + (value - minimum) / (maximum - minimum) * (high - low))


def _new_canvas(width: int, height: int, color: Color) -> list[list[Color]]:
    return [[color for _column in range(width)] for _row in range(height)]


def _rect(
    canvas: list[list[Color]],
    x: int,
    y: int,
    width: int,
    height: int,
    color: Color,
) -> None:
    for row in range(max(0, y), min(len(canvas), y + height)):
        for column in range(max(0, x), min(len(canvas[0]), x + width)):
            canvas[row][column] = color


def _line(
    canvas: list[list[Color]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: Color,
) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = dx + dy
    current_x, current_y = x0, y0
    while True:
        if 0 <= current_y < len(canvas) and 0 <= current_x < len(canvas[0]):
            canvas[current_y][current_x] = color
        if current_x == x1 and current_y == y1:
            break
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            current_x += step_x
        if doubled <= dx:
            error += dx
            current_y += step_y


def _write_png(path: Path, canvas: list[list[Color]]) -> None:
    height = len(canvas)
    width = len(canvas[0])
    raw = b"".join(b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in canvas)
    payload = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw, level=9)),
            _chunk(b"IEND", b""),
        )
    )
    path.write_bytes(payload)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack("!I", len(payload))
        + kind
        + payload
        + struct.pack("!I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )
