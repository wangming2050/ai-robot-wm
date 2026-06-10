#!/usr/bin/env python3
"""Week 14 mobile remote maze simulation.

Run this file, then open http://127.0.0.1:8014 on a computer or
http://<tailscale-ip>:8014 from a phone in the same Tailnet.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar


MAZE = [
    "###########",
    "#S  #     #",
    "### # ### #",
    "#   # #   #",
    "# ### # ###",
    "# #   #   #",
    "# # ##### #",
    "# #     # #",
    "# ##### # #",
    "#     #  G#",
    "###########",
]

DIRECTIONS = ["north", "east", "south", "west"]
DELTA = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}


@dataclass
class MazeRobot:
    x: int = 1
    y: int = 1
    heading: str = "east"
    auto: bool = False
    collisions: int = 0
    message: str = "Ready."
    trail: list[dict[str, int]] = field(default_factory=lambda: [{"x": 1, "y": 1}])

    def reset(self) -> None:
        self.x = 1
        self.y = 1
        self.heading = "east"
        self.auto = False
        self.collisions = 0
        self.message = "Reset to start."
        self.trail = [{"x": 1, "y": 1}]

    def turn_left(self) -> None:
        index = DIRECTIONS.index(self.heading)
        self.heading = DIRECTIONS[(index - 1) % len(DIRECTIONS)]
        self.message = f"Turn left, heading {self.heading}."

    def turn_right(self) -> None:
        index = DIRECTIONS.index(self.heading)
        self.heading = DIRECTIONS[(index + 1) % len(DIRECTIONS)]
        self.message = f"Turn right, heading {self.heading}."

    def turn_back(self) -> None:
        index = DIRECTIONS.index(self.heading)
        self.heading = DIRECTIONS[(index + 2) % len(DIRECTIONS)]
        self.message = f"Turn back, heading {self.heading}."

    def move(self, direction: int = 1) -> bool:
        dx, dy = DELTA[self.heading]
        nx = self.x + dx * direction
        ny = self.y + dy * direction
        if self.is_wall(nx, ny):
            self.collisions += 1
            self.message = f"Blocked by wall at ({nx}, {ny})."
            return False
        self.x = nx
        self.y = ny
        self.trail.append({"x": self.x, "y": self.y})
        self.message = f"Move to ({self.x}, {self.y})."
        if self.goal_reached:
            self.auto = False
            self.message = "Goal reached!"
        return True

    @property
    def goal_reached(self) -> bool:
        return MAZE[self.y][self.x] == "G"

    def is_wall(self, x: int, y: int) -> bool:
        if y < 0 or y >= len(MAZE) or x < 0 or x >= len(MAZE[0]):
            return True
        return MAZE[y][x] == "#"

    def can_move(self, heading: str) -> bool:
        dx, dy = DELTA[heading]
        return not self.is_wall(self.x + dx, self.y + dy)

    def auto_step(self) -> None:
        if self.goal_reached:
            self.auto = False
            self.message = "Goal reached, auto mode stopped."
            return
        current = DIRECTIONS.index(self.heading)
        right = DIRECTIONS[(current + 1) % len(DIRECTIONS)]
        left = DIRECTIONS[(current - 1) % len(DIRECTIONS)]
        if self.can_move(right):
            self.turn_right()
            self.move()
        elif self.can_move(self.heading):
            self.move()
        elif self.can_move(left):
            self.turn_left()
            self.move()
        else:
            self.turn_back()

    def apply_command(self, command: str) -> None:
        if command == "forward":
            self.auto = False
            self.move(1)
        elif command == "back":
            self.auto = False
            self.move(-1)
        elif command == "left":
            self.auto = False
            self.turn_left()
        elif command == "right":
            self.auto = False
            self.turn_right()
        elif command == "stop":
            self.auto = False
            self.message = "Stop."
        elif command == "auto":
            self.auto = not self.auto
            self.message = "Auto exploration enabled." if self.auto else "Manual mode enabled."
        elif command == "reset":
            self.reset()
        else:
            self.message = f"Unknown command: {command}"

    def state(self) -> dict:
        return {
            "maze": MAZE,
            "robot": {"x": self.x, "y": self.y, "heading": self.heading},
            "auto": self.auto,
            "collisions": self.collisions,
            "trail": self.trail[-200:],
            "goal_reached": self.goal_reached,
            "message": self.message,
        }


ROBOT = MazeRobot()


class MazeHandler(BaseHTTPRequestHandler):
    server_version = "Week14MazeRemote/1.0"
    html_path: ClassVar[Path] = Path(__file__).with_name("remote_controller.html")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send_bytes(self.html_path.read_bytes(), "text/html; charset=utf-8")
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
        if ROBOT.auto and now - last_step >= 0.35:
            ROBOT.auto_step()
            last_step = now
        time.sleep(0.05)


def main() -> None:
    import threading

    threading.Thread(target=run_auto_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 8014), MazeHandler)
    print("Week 14 maze remote server")
    print("Computer: http://127.0.0.1:8014")
    print("Phone:    http://<tailscale-or-lan-ip>:8014")
    server.serve_forever()


if __name__ == "__main__":
    main()
