# -*- coding: utf-8 -*-
"""
Ядро калькулятора зарплаты с отгулами (без UI).
Полностью повторяет app/calculator_core.js и браузерную версию.

Модель выплат:
  * аванс 20 числа  = доля оклада + вся премия (премия считается от фактически отработанного)
  * зарплата 5 числа = остаток оклада + надбавка за вредность − НДФЛ − доп. вычеты
"""

from datetime import date, timedelta

MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
          "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# нерабочие праздничные дни, ст. 112 ТК РФ
HOLIDAYS = {
    2024: {(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(2,23),(3,8),(5,1),(5,9),(6,12),(11,4)},
    2025: {(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(2,23),(3,8),(5,1),(5,9),(6,12),(11,4)},
    2026: {(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(2,23),(3,8),(5,1),(5,9),(6,12),(11,4)},
    2027: {(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(2,23),(3,8),(5,1),(5,9),(6,12),(11,4)},
}

# надбавка за вредность по расчётным листам: авг 1896 ₽ / 14 дн, сен 3005 ₽ / 22 дн
HARM_BY_PAYSLIP = (1896 + 3005) / (14 + 22)  # ≈ 136.01 ₽/день


def workdays_in_month(year: int, month_idx: int) -> int:
    """Рабочие дни (пятидневка) для месяца. month_idx: 0=январь."""
    hol = HOLIDAYS.get(year, set())
    d = date(year, month_idx + 1, 1)
    n = 0
    while d.month == month_idx + 1:
        if d.weekday() < 5 and (d.month, d.day) not in hol:
            n += 1
        d += timedelta(days=1)
    return n


def compute_pay(s: dict) -> dict:
    """Главный расчёт. Ключи состояния — как в JS-версии."""
    oklad   = float(s.get("salary") or 0)
    b_pct   = (float(s.get("bonusPct") or 0)) / 100.0
    harm_pd = float(s.get("harmPerDay") or 0)
    harm_fix = bool(s.get("harmFixed"))
    if s.get("workdaysSel") == "manual":
        wd = max(1, int(float(s.get("workdaysManual") or 1)))
    else:
        wd = workdays_in_month(int(float(s.get("year") or 2026)), int(float(s.get("month") or 0)))
    otg   = max(0.0, float(s.get("otg") or 0))
    sick  = max(0.0, float(s.get("sick") or 0))
    extra = float(s.get("extraDeduct") or 0)
    adv_sh = min(max((float(s.get("advShare") or 0)) / 100.0, 0.0), 1.0)
    ndfl   = min(max((float(s.get("ndfl") or 0)) / 100.0, 0.0), 1.0)

    absent = min(otg + sick, wd)
    worked = max(wd - absent, 0.0)

    # стоимость одного дня отсутствия (на руки)
    oklad_day = oklad / wd
    bonus_day = oklad_day * b_pct
    harm_day_eff = 0.0 if harm_fix else harm_pd  # фикс. вредность от отгулов не уменьшается
    gross_day = oklad_day + bonus_day + harm_day_eff
    net_day = gross_day * (1 - ndfl)

    def scenario(days_worked, extra_amt):
        oklad_gross = oklad * (days_worked / wd)
        bonus_gross = oklad_gross * b_pct
        harm_final = (harm_pd * wd if days_worked > 0 else 0.0) if harm_fix else harm_pd * days_worked
        gross = oklad_gross + bonus_gross + harm_final - extra_amt
        tax = max(gross, 0.0) * ndfl
        net = max(gross, 0.0) - tax
        sal_gross = oklad_gross * (1 - adv_sh) + harm_final - extra_amt
        sal_net = max(sal_gross - tax, 0.0)
        adv_net = net - sal_net  # остаток условно показываем как аванс 20 числа
        return {"oklad_gross": oklad_gross, "bonus_gross": bonus_gross, "harm": harm_final,
                "gross": gross, "tax": tax, "net": net, "adv_net": adv_net,
                "sal_net": sal_net, "sal_gross": sal_gross}

    p = scenario(worked, extra)
    pf = scenario(wd, 0.0)
    loss = pf["net"] - p["net"]

    rows = [
        [f"Оклад ({worked:g} из {wd} дн.)", pf["oklad_gross"], p["oklad_gross"]],
        [f"Премия {float(s.get('bonusPct') or 0):g}%", pf["bonus_gross"], p["bonus_gross"]],
        [("Надбавка за вредность (фикс.)" if harm_fix
          else f"Надбавка за вредность ({worked:g} дн.)"), pf["harm"], p["harm"]],
        ["Доп. вычеты", 0.0, -extra],
        [f"НДФЛ {ndfl*100:g}%", -pf["tax"], -p["tax"]],
    ]

    return {
        "WD": wd, "absent": absent, "worked": worked,
        "okladDay": oklad_day, "bonusDay": bonus_day, "harmDay": harm_day_eff,
        "taxBack": gross_day * ndfl, "costPerDay": net_day,
        "net": p["net"], "loss": loss, "netNoLoss": pf["net"],
        "advNet": p["adv_net"], "salNet": p["sal_net"],
        "pfAdvNet": max(pf["net"], 0.0) - max(pf["sal_gross"] - pf["tax"], 0.0), "pfSalNet": max(pf["sal_gross"] - pf["tax"], 0.0),
        "rows": rows, "harmFix": harm_fix,
    }
