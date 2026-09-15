#!/usr/bin/env python3
"""Backward-compatible wrapper. The governed converter is excel_to_json.py."""
from excel_to_json import main

if __name__ == "__main__":
    raise SystemExit(main())
