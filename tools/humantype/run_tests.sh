#!/usr/bin/env sh
# Run the suite with nothing installed but the standard library.
set -e
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -t . "$@"
