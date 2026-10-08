from __future__ import annotations


NORMALIZED_SIZE = 1000


def _round_half_up(numerator: int, denominator: int) -> int:
    """Round a non-negative rational number without banker's-rounding drift."""
    return (2 * numerator + denominator) // (2 * denominator)


def denormalize_coordinate(
    coordinate: tuple[int, int],
    width: int,
    height: int,
) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError("display dimensions must be positive")
    x, y = coordinate
    if not (0 <= x <= NORMALIZED_SIZE and 0 <= y <= NORMALIZED_SIZE):
        raise ValueError("normalized coordinates must be within 0..1000")
    actual_x = min(width - 1, _round_half_up(x * (width - 1), NORMALIZED_SIZE))
    actual_y = min(height - 1, _round_half_up(y * (height - 1), NORMALIZED_SIZE))
    return actual_x, actual_y


def normalize_coordinate(
    coordinate: tuple[int, int],
    width: int,
    height: int,
) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError("display dimensions must be positive")
    x, y = coordinate
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("display coordinates are outside the screen")
    normalized_x = _round_half_up(x * NORMALIZED_SIZE, max(1, width - 1))
    normalized_y = _round_half_up(y * NORMALIZED_SIZE, max(1, height - 1))
    return normalized_x, normalized_y
