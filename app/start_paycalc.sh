#!/usr/bin/env bash
# Запуск калькулятора (Linux/macOS). Сначала: pip install PySide6
cd "$(dirname "$0")"
exec python3 paycalc.py "$@"
