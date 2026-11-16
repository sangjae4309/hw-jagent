#!/usr/bin/env bash
# Usage: /path/to/environment/install.sh /path/to/project [--dry-run|--update]
set -euo pipefail
base="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -eq 0 || "$1" == -* ]]; then
    target="$PWD"
else
    target="$1"
    shift
fi
python="${PYTHON:-python3}"
"$python" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else "Python 3.8+ is required")'
exec "$python" "$base/tools/agentctl.py" install --repo "$target" "$@"
