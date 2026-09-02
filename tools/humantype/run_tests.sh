#!/usr/bin/env sh
# Run the suite with nothing installed but the standard library.
# SyntaxWarning is promoted to an error: invalid escape sequences behave
# correctly today, warn on every import, and become errors in a later Python.
set -e
cd "$(dirname "$0")"
exec python3 -W error::SyntaxWarning -m unittest discover -s tests -t . "$@"
