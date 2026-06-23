"""Maze configuration and collision helpers for Week 14.

The scoring checklist expects a dedicated maze.py file.  This module keeps the
map, start/goal points, movement directions, and reusable collision logic in
one place so the server and explorer share the same world model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


MAZE_GRID = [
    "###########",
    "#S  #     #",
    "### # ### #",
    "#   # #   #",
    "# ### # ###",
    "# #   #   #",
    "# # ##### #",
    "# #     # #",
    "# ##### # #",
    "#        G#",
    "###########",
]

DIRECTIONS = ["north", "east", "south", "west"]

DELTA = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def as_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


def find_tile(tile: str) -> Point:
    for y, row in enumerate(MAZE_GRID):
        x = row.find(tile)
        if x >= 0:
            return Point(x, y)
    raise ValueError(f"maze tile {tile!r} not found")


START = find_tile("S")
GOAL = find_tile("G")


def width() -> int:
    return len(MAZE_GRID[0])


def height() -> int:
    return len(MAZE_GRID)


def in_bounds(point: Point) -> bool:
    return 0 <= point.x < width() and 0 <= point.y < height()


def is_wall(point: Point) -> bool:
    if not in_bounds(point):
        return True
    return MAZE_GRID[point.y][point.x] == "#"


def is_goal(point: Point) -> bool:
    return point == GOAL


def step(point: Point, heading: str, distance: int = 1) -> Point:
    dx, dy = DELTA[heading]
    return Point(point.x + dx * distance, point.y + dy * distance)


def can_move(point: Point, heading: str) -> bool:
    return not is_wall(step(point, heading))


def neighbors(point: Point) -> Iterable[tuple[str, Point]]:
    for heading in DIRECTIONS:
        candidate = step(point, heading)
        if not is_wall(candidate):
            yield heading, candidate


def export_grid() -> list[str]:
    return list(MAZE_GRID)
