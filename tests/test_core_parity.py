# -*- coding: utf-8 -*-
"""Сверка Python-ядра (app/calculator_core.py) и JS-ядра (app/calculator_core.js).
Запуск:  python3 tests/test_core_parity.py
Нужен Node.js для генерации эталона: node tests/gen_js_golden.js > tests/js_golden.json
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "app"))
from calculator_core import compute_pay, workdays_in_month

CASES = []
for year in (2025, 2026):
    for month in range(12):
        CASES.append({"year": year, "month": month, "otg": 3})
CASES += [
    {"salary": 79000, "bonusPct": 20, "harmPerDay": 136.01, "harmFixed": False,
     "year": 2026, "month": 9, "otg": 0, "sick": 0, "extraDeduct": 0,
     "workdaysSel": "auto", "workdaysManual": 22, "advShare": 50, "ndfl": 13},
    {"salary": 79000, "bonusPct": 20, "harmPerDay": 136.01, "harmFixed": True,
     "year": 2026, "month": 9, "otg": 4.5, "sick": 2, "extraDeduct": 1500,
     "workdaysSel": "manual", "workdaysManual": 21, "advShare": 40, "ndfl": 13},
    {"salary": 50000, "bonusPct": 0, "harmPerDay": 0, "harmFixed": False,
     "year": 2026, "month": 0, "otg": 31, "sick": 0, "extraDeduct": 0,
     "workdaysSel": "auto", "workdaysManual": 22, "advShare": 50, "ndfl": 13},
]

def run_js():
    gen = os.path.join(HERE, "gen_js_golden.js")
    out = subprocess.run(["node", gen], capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def main():
    js = run_js()
    bad = 0
    for st, ref in zip(CASES, js):
        r = compute_pay(st)
        for k in ("WD", "absent", "worked", "costPerDay", "net", "loss", "netNoLoss", "advNet", "salNet"):
            if abs(r[k] - ref[k]) > 1e-6:
                print(f"MISMATCH {k}: py={r[k]} js={ref[k]} state={st}")
                bad += 1
    # контрольные значения из прошлой ручной сверки: 22 раб. дня, 3 отгула
    ctl = compute_pay({**CASES[-3], "workdaysSel": "manual", "workdaysManual": 22, "otg": 3})
    assert abs(ctl["netNoLoss"] - 85079.19) < 0.5, ctl["netNoLoss"]
    assert abs(ctl["net"] - 73477.66) < 0.5, ctl["net"]
    assert abs(ctl["costPerDay"] - 3867.17) < 0.5, ctl["costPerDay"]
    if bad == 0:
        print(f"OK: py/js parity on {len(CASES)} cases; control values match.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
