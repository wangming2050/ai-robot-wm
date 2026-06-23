#!/usr/bin/env python3
"""Week 14 phone remote server.

Run this single long-lived program, then open http://127.0.0.1:8014 or
http://<computer-lan-ip>:8014 from a phone on the same network.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from explorer import path_to_commands, shortest_path
from maze import DELTA, DIRECTIONS, GOAL, START, Point, can_move, export_grid, is_goal, is_wall, step


HOST = "0.0.0.0"
PORT = 8014


@dataclass
class MazeRobot:
    position: Point = START
    heading: str = "east"
    auto: bool = False
    collisions: int = 0
    message: str = "Ready."
    trail: list[Point] = field(default_factory=lambda: [START])
    planned_path: list[Point] = field(default_factory=list)
    command_queue: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.position = START
        self.heading = "east"
        self.auto = False
        self.collisions = 0
        self.message = "Reset to start."
        self.trail = [START]
        self.planned_path = []
        self.command_queue = []

    def turn_left(self) -> None:
        index = DIRECTIONS.index(self.heading)
        self.heading = DIRECTIONS[(index - 1) % len(DIRECTIONS)]
        self.message = f"Turn left, heading {self.heading}."

    def turn_right(self) -> None:
        index = DIRECTIONS.index(self.heading)
        self.heading = DIRECTIONS[(index + 1) % len(DIRECTIONS)]
        self.message = f"Turn right, heading {self.heading}."

    def move(self, distance: int = 1) -> bool:
        target = step(self.position, self.heading, distance)
        if is_wall(target):
            self.collisions += 1
            self.message = f"Collision blocked at ({target.x}, {target.y})."
            return False

        self.position = target
        self.trail.append(target)
        self.message = f"Move to ({target.x}, {target.y})."
        if is_goal(target):
            self.auto = False
            self.command_queue = []
            self.message = "Goal reached!"
        return True

    def apply_command(self, command: str, from_auto: bool = False) -> None:
        if not from_auto and command not in {"auto", "explore"}:
            self.auto = False
            self.command_queue = []

        if command == "forward":
            self.move(1)
        elif command == "back":
            self.move(-1)
        elif command == "left":
            self.turn_left()
        elif command == "right":
            self.turn_right()
        elif command == "stop":
            self.auto = False
            self.command_queue = []
            self.message = "Stop."
        elif command in {"auto", "explore"}:
            self.start_bfs_explorer()
        elif command == "reset":
            self.reset()
        else:
            self.message = f"Unknown command: {command}"

    def start_bfs_explorer(self) -> None:
        path = shortest_path(self.position, GOAL)
        if not path:
            self.auto = False
            self.command_queue = []
            self.message = "No path to goal."
            return

        self.planned_path = path
        self.command_queue = path_to_commands(path, self.heading)
        self.auto = bool(self.command_queue)
        self.message = f"BFS planned {len(path) - 1} steps to goal."
        if not self.command_queue:
            self.message = "Already at goal."

    def auto_step(self) -> None:
        if not self.auto:
            return
        if is_goal(self.position):
            self.auto = False
            self.message = "Goal reached, auto mode stopped."
            return
        if not self.command_queue:
            self.start_bfs_explorer()
            return
        self.apply_command(self.command_queue.pop(0), from_auto=True)

    def state(self) -> dict:
        return {
            "maze": export_grid(),
            "robot": {"x": self.position.x, "y": self.position.y, "heading": self.heading},
            "auto": self.auto,
            "collisions": self.collisions,
            "trail": [point.as_dict() for point in self.trail[-300:]],
            "planned_path": [point.as_dict() for point in self.planned_path],
            "goal": GOAL.as_dict(),
            "goal_reached": is_goal(self.position),
            "front_blocked": not can_move(self.position, self.heading),
            "message": self.message,
        }


ROBOT = MazeRobot()


class RemoteHandler(BaseHTTPRequestHandler):
    server_version = "Week14Remote/2.0"
    index_path: ClassVar[Path] = Path(__file__).with_name("index.html")

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_bytes(self.index_path.read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/state":
            self._send_json(ROBOT.state())
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {}
        ROBOT.apply_command(str(payload.get("command", "")))
        self._send_json(ROBOT.state())

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {self.client_address[0]} {fmt % args}")

    def _send_json(self, data: dict) -> None:
        self._send_bytes(json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_auto_loop() -> None:
    last_step = 0.0
    while True:
        now = time.time()
        if ROBOT.auto and now - last_step >= 0.28:
            ROBOT.auto_step()
            last_step = now
        time.sleep(0.04)


def main() -> None:
    threading.Thread(target=run_auto_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), RemoteHandler)
    print("Week 14 phone remote maze server")
    print(f"Computer: http://127.0.0.1:{PORT}")
    print(f"Phone:    http://<lan-or-tailscale-ip>:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

