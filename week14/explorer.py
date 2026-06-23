"""Automatic maze exploration for Week 14.

The explorer uses BFS so the robot can plan a shortest path to the goal.  The
server consumes the path one step at a time, which keeps automatic exploration
visible in the browser instead of teleporting directly to the finish.
"""

from __future__ import annotations

from collections import deque

from maze import DIRECTIONS, Point, neighbors


def shortest_path(start: Point, goal: Point) -> list[Point]:
    """Return a shortest walkable path from start to goal, including both."""
    if start == goal:
        return [start]

    queue: deque[Point] = deque([start])
    previous: dict[Point, Point | None] = {start: None}

    while queue:
        current = queue.popleft()
        for _, candidate in neighbors(current):
            if candidate in previous:
                continue
            previous[candidate] = current
            if candidate == goal:
                return _reconstruct_path(previous, candidate)
            queue.append(candidate)

    return []


def _reconstruct_path(previous: dict[Point, Point | None], end: Point) -> list[Point]:
    path = [end]
    current = end
    while previous[current] is not None:
        current = previous[current]
        path.append(current)
    path.reverse()
    return path


def heading_between(a: Point, b: Point) -> str:
    dx = b.x - a.x
    dy = b.y - a.y
    if (dx, dy) == (0, -1):
        return "north"
    if (dx, dy) == (1, 0):
        return "east"
    if (dx, dy) == (0, 1):
        return "south"
    if (dx, dy) == (-1, 0):
        return "west"
    raise ValueError(f"points are not adjacent: {a} -> {b}")


def turns_to_face(current_heading: str, target_heading: str) -> list[str]:
    current = DIRECTIONS.index(current_heading)
    target = DIRECTIONS.index(target_heading)
    diff = (target - current) % len(DIRECTIONS)
    if diff == 0:
        return []
    if diff == 1:
        return ["right"]
    if diff == 2:
        return ["right", "right"]
    return ["left"]


def path_to_commands(path: list[Point], current_heading: str) -> list[str]:
    """Convert a planned path into left/right/forward commands."""
    commands: list[str] = []
    heading = current_heading
    for a, b in zip(path, path[1:]):
        target = heading_between(a, b)
        turns = turns_to_face(heading, target)
        commands.extend(turns)
        commands.append("forward")
        heading = target
    return commands

