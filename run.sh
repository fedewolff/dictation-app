#!/bin/bash
# Run the dictation app

cd "$(dirname "$0")"
source venv/bin/activate
python3 -m src.main "$@"
