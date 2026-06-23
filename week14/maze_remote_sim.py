#!/usr/bin/env python3
"""Backward-compatible entrypoint.

The course checklist now expects week14/server.py.  This wrapper keeps the old
file runnable while delegating the actual long-lived program to server.py.
"""

from server import main


if __name__ == "__main__":
    main()
