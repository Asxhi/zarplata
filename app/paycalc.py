#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💸 Калькулятор зарплаты с отгулами — десктопное приложение.

Запуск:            python paycalc.py
Иконка на рабочем столе (Windows): запуск «Калькулятор зарплаты.vbs» из этой папки.
Иконка на рабочем столе (Linux):   запуск start_paycalc.sh / desktop-файл.

Требования: Python 3.8+ и PySide6 (pip install PySide6).
Данные сохраняются в ~/.paycalc.json — ничего не уходит наружу.
"""

import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calculator_core import MONTHS, HARM_BY_PAYSLIP, compute_pay, workdays_in_month

def config_path() -> str:
    """Файл настроек. HOME читаем динамически — так удобнее тестировать и переносить."""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(home, ".paycalc.json")

DARK_QSS = """
QMainWindow, QWidget { background: #0f1420; color: #e8edf6; }
QLabel { color: #e8edf6; }
QLabel.muted { color: #8fa0bd; font-size: 12px; }
QLabel.h2 { color: #4da3ff; font-weight: 700; font-size: 14px; }
QLabel.big { font-size: 26px; font-weight: 800; }
QLabel.good { color: #3ecf8e; }
QLabel.bad { color: #ff6b6b; }
QGroupBox {
    border: 1px solid #2e3b57; border-radius: 12px; margin-top: 14px;
    padding-top: 6px; background: #1a2233; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #4da3ff; }
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {
    background: #212c42; border: 1px solid #2e3b57; border-radius: 8px;
    padding: 6px 8px; color: #e8edf6; selection-background-color: #4da3ff;
}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border-color: #4da3ff; }
QComboBox QAbstractItemView { background: #212c42; color: #e8edf6;
    selection-background-color: #2e3b57; }
QPushButton {
    background: #212c42; border: 1px solid #2e3b57; border-radius: 8px;
    padding: 6px 12px; color: #4da3ff;
}
QPushButton:hover { border-color: #4da3ff; }
QTableWidget {
    background: #1a2233; border: 1px solid #2e3b57; border-radius: 8px;
    gridline-color: #2e3b57; color: #e8edf6;
}
QHeaderView::section { background: #212c42; color: #8fa0bd; border: none; padding: 6px; }
QCheckBox { color: #8fa0bd; }
"""


def money(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "\u00a0").replace(".", ",")
    return s + " \u00a0₽"


class PayCalc(QMainWindow):
    DEFAULTS = {
        "salary": 79000.0, "bonusPct": 20.0, "harmPerDay": round(HARM_BY_PAYSLIP, 2),
        "harmFixed": False, "year": 2026, "otg": 0.0, "sick": 0.0,
        "extraDeduct": 0.0, "workdaysSel": "auto", "workdaysManual": 22,
        "advShare": 50.0, "ndfl": 13.0,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор зарплаты с отгулами")
        self.resize(980, 720)
        self.setStyleSheet(DARK_QSS)
        self._updating = False
        self._build_ui()
        self._load_config()
        self.recalc()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 10, 14, 14)
        outer.setSpacing(10)

        title = QLabel("💸 Калькулятор зарплаты с отгулами")
        f = QFont(); f.setPointSize(15); f.setBold(True); title.setFont(f)
        outer.addWidget(title)
        sub = QLabel("Аванс — 20 числа (в него входит премия 20%), зарплата — 5 числа.\n"
                     "Напишите, сколько отгулов взяли, — сразу видно, сколько теряете и что получите на руки.")
        sub.setProperty("class", "muted")
        sub.setStyleSheet("color:#8fa0bd;")
        outer.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(10)
        outer.addLayout(grid, 1)

        # --- карточка: расчётный месяц ---
        box1 = QGroupBox("📅 Расчётный месяц")
        f1 = QFormLayout(box1); f1.setSpacing(8)
        self.year = QSpinBox(); self.year.setRange(2000, 2100)
        self.month = QComboBox(); self.month.addItems(MONTHS)
        self.wd_info = QLabel("—"); self.wd_info.setStyleSheet("color:#8fa0bd;")
        self.otg = QDoubleSpinBox(); self.otg.setRange(0, 31); self.otg.setSingleStep(0.5)
        self.otg.setDecimals(1); self.otg.setSuffix(" дн.")
        self.sick = QDoubleSpinBox(); self.sick.setRange(0, 31); self.sick.setSingleStep(0.5)
        self.sick.setDecimals(1); self.sick.setSuffix(" дн.")
        self.extra = QDoubleSpinBox(); self.extra.setRange(-1_000_000, 1_000_000)
        self.extra.setSuffix(" ₽")
        f1.addRow("Год", self.year)
        f1.addRow("Месяц", self.month)
        f1.addRow("Рабочих дней:", self.wd_info)
        f1.addRow("Отгулов взял", self.otg)
        f1.addRow("Больничных дней", self.sick)
        f1.addRow("Доп. вычеты", self.extra)
        grid.addWidget(box1, 0, 0)

        # --- карточка: настройки ---
        box2 = QGroupBox("⚙️ Настройки")
        f2 = QFormLayout(box2); f2.setSpacing(8)
        self.salary = QDoubleSpinBox(); self.salary.setRange(0, 10_000_000)
        self.salary.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.salary.setSuffix(" ₽")
        self.bonus_pct = QDoubleSpinBox(); self.bonus_pct.setRange(0, 100); self.bonus_pct.setSuffix(" %")
        self.harm_fixed = QCheckBox("Вредность фиксированная (не режется отгулами)")
        self.harm_per_day = QDoubleSpinBox(); self.harm_per_day.setRange(0, 100_000)
        self.harm_per_day.setSuffix(" ₽/день")
        btn_harm = QPushButton("Пересчитать по расчётным листам (авг/сен)")
        btn_harm.clicked.connect(self._recalc_harm)
        self.wd_sel = QComboBox()
        self.wd_sel.addItem("Авто: производственный календарь РФ", "auto")
        self.wd_sel.addItem("Задать вручную", "manual")
        self.wd_manual = QSpinBox(); self.wd_manual.setRange(1, 31)
        f2.addRow("Оклад", self.salary)
        f2.addRow("Премия (% от оклада)", self.bonus_pct)
        f2.addRow(self.harm_fixed)
        f2.addRow("Вредность ₽/день", self.harm_per_day)
        f2.addRow(btn_harm)
        f2.addRow("Рабочих дней", self.wd_sel)
        f2.addRow("Количество дней", self.wd_manual)
        grid.addWidget(box2, 0, 1)

        # --- карточка: стоимость отгула ---
        box3 = QGroupBox("🧮 Сколько стоит один отгул")
        v3 = QVBoxLayout(box3)
        self.cost_per_day = QLabel("—")
        self.cost_per_day.setProperty("class", "big")
        self.cost_per_day.setStyleSheet("font-size:26px;font-weight:800;color:#ff6b6b;")
        v3.addWidget(self.cost_per_day)
        self.r_oklad_day = self._row(v3, "Оклад за 1 рабочий день")
        self.r_bonus_day = self._row(v3, "Премия за 1 день")
        self.r_harm_day = self._row(v3, "Вредность за 1 день")
        self.r_tax_back = self._row(v3, "Экономия на НДФЛ")
        self.formula_lbl = QLabel("")
        self.formula_lbl.setStyleSheet("color:#8fa0bd;font-size:12px;")
        self.formula_lbl.setWordWrap(True)
        v3.addWidget(self.formula_lbl)
        v3.addStretch(1)
        grid.addWidget(box3, 1, 0)

        # --- карточка: итог ---
        box4 = QGroupBox("💰 Что получится в этом месяце")
        v4 = QVBoxLayout(box4)
        net_cap = QLabel("Итого на руки за месяц")
        net_cap.setStyleSheet("color:#8fa0bd;")
        v4.addWidget(net_cap)
        self.net_total = QLabel("—")
        self.net_total.setStyleSheet("font-size:28px;font-weight:800;color:#3ecf8e;")
        v4.addWidget(self.net_total)
        self.r_loss = self._row(v4, "Потери из-за отсутствия")
        self.r_no_loss = self._row(v4, "Если бы отгулов не было")
        self.r_adv = self._row(v4, "Аванс 20 числа (на руки)")
        self.r_sal = self._row(v4, "Зарплата 5 числа (на руки)")
        hint4 = QLabel("«Если бы отгулов не было» — тот же месяц при полной отработке.")
        hint4.setStyleSheet("color:#8fa0bd;font-size:12px;")
        hint4.setWordWrap(True)
        v4.addWidget(hint4)
        v4.addStretch(1)
        grid.addWidget(box4, 1, 1)

        # --- детализация ---
        box5 = QGroupBox("📆 Детализация")
        v5 = QVBoxLayout(box5)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Статья", "Было бы (без отгулов)", "Факт", "Δ Потеря"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        v5.addWidget(self.table)

        foot = QHBoxLayout()
        lbl_adv = QLabel("Доля оклада в авансе, %"); lbl_adv.setStyleSheet("color:#8fa0bd;")
        self.adv_share = QDoubleSpinBox(); self.adv_share.setRange(0, 100); self.adv_share.setSuffix(" %")
        lbl_ndfl = QLabel("НДФЛ, %"); lbl_ndfl.setStyleSheet("color:#8fa0bd;")
        self.ndfl = QDoubleSpinBox(); self.ndfl.setRange(0, 50); self.ndfl.setSuffix(" %")
        foot.addWidget(lbl_adv); foot.addWidget(self.adv_share)
        foot.addSpacing(24); foot.addWidget(lbl_ndfl); foot.addWidget(self.ndfl)
        foot.addStretch(1)
        v5.addLayout(foot)
        hint5 = QLabel(
            "Модель выплат: аванс 20 числа = доля оклада + вся премия; зарплата 5 числа = остаток\n"
            "оклада + вредность − НДФЛ − доп. вычеты. Оценка приблизительная — точные суммы\n"
            "зависят от политики компании.")
        hint5.setStyleSheet("color:#8fa0bd;font-size:12px;")
        v5.addWidget(hint5)
        grid.addWidget(box5, 2, 0, 1, 2)

        grid.setRowStretch(0, 1); grid.setRowStretch(1, 1); grid.setRowStretch(2, 2)
        self.setCentralWidget(root)

        for w in (self.year, self.month, self.otg, self.sick, self.extra, self.salary,
                  self.bonus_pct, self.harm_per_day, self.harm_fixed, self.wd_sel,
                  self.wd_manual, self.adv_share, self.ndfl):
            if isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.recalc)
            elif isinstance(w, QCheckBox):
                w.toggled.connect(self.recalc)
            else:
                w.valueChanged.connect(self.recalc)
        self.wd_sel.currentIndexChanged.connect(self._toggle_manual_wd)

    def _row(self, layout, caption):
        h = QHBoxLayout()
        cap = QLabel(caption); cap.setStyleSheet("color:#8fa0bd;")
        val = QLabel("—"); val.setStyleSheet("font-weight:600;")
        h.addWidget(cap); h.addStretch(1); h.addWidget(val)
        layout.addLayout(h)
        return val

    # ---------------- логика ----------------
    def _state(self):
        return {
            "salary": self.salary.value(), "bonusPct": self.bonus_pct.value(),
            "harmPerDay": self.harm_per_day.value(), "harmFixed": self.harm_fixed.isChecked(),
            "year": self.year.value(), "month": self.month.currentIndex(),
            "otg": self.otg.value(), "sick": self.sick.value(),
            "extraDeduct": self.extra.value(),
            "workdaysSel": self.wd_sel.currentData(), "workdaysManual": self.wd_manual.value(),
            "advShare": self.adv_share.value(), "ndfl": self.ndfl.value(),
        }

    def _recalc_harm(self):
        self.harm_per_day.setValue(round(HARM_BY_PAYSLIP, 2))

    def _toggle_manual_wd(self):
        manual = self.wd_sel.currentData() == "manual"
        self.wd_manual.setEnabled(manual)

    def recalc(self):
        if self._updating:
            return
        s = self._state()
        r = compute_pay(s)

        wd_txt = f"{r['WD']} дн. ({MONTHS[s['month']]} {s['year']})"
        self.wd_info.setText(wd_txt)
        self._toggle_manual_wd()

        self.cost_per_day.setText(money(r["costPerDay"]))
        self.r_oklad_day.setText(money(r["okladDay"]))
        self.r_bonus_day.setText(money(r["bonusDay"]))
        self.r_harm_day.setText("0 ₽ (фикс.)" if r["harmFix"] else money(s["harmPerDay"]))
        self.r_tax_back.setText("−" + money(r["taxBack"]))
        per_gross = (r["okladDay"] * (1 + s["bonusPct"] / 100.0)
                     + (0 if r["harmFix"] else s["harmPerDay"]))
        oklad_txt = f"{s['salary']:,.0f}".replace(",", "\u00a0")
        harm_txt = f"{s['harmPerDay']:,.2f}".replace(",", "\u00a0").replace(".", ",")
        formula = (f"(оклад {oklad_txt} / {r['WD']} × {1 + s['bonusPct']/100:.2f}"
                   + ("" if r["harmFix"] else f" + {harm_txt}")
                   + f") × (1 − {s['ndfl']:g}%) ≈ {money(per_gross * (1 - s['ndfl']/100))}"
                     " за 1 день отгула на руки")
        self.formula_lbl.setText(formula)

        self.net_total.setText(money(r["net"]))
        self.r_loss.setText("−" + money(r["loss"]))
        self.r_loss.setStyleSheet("font-weight:600;color:#ff6b6b;" if r["loss"] > 0.005 else "font-weight:600;")
        self.r_no_loss.setText(money(r["netNoLoss"]))
        self.r_adv.setText(money(r["advNet"]))
        self.r_sal.setText(money(r["salNet"]))

        rows = list(r["rows"])
        rows.append(["Аванс 20 числа (на руки)", r["pfAdvNet"], r["advNet"]])
        rows.append(["Зарплата 5 числа (на руки)", r["pfSalNet"], r["salNet"]])
        rows.append(["ИТОГО на руки", r["netNoLoss"], r["net"]])
        self.table.setRowCount(len(rows))
        for i, (name, before, fact) in enumerate(rows):
            delta = fact - before
            items = [QTableWidgetItem(name), QTableWidgetItem(money(before)),
                     QTableWidgetItem(money(fact)),
                     QTableWidgetItem("—" if abs(delta) < 0.005 else money(delta))]
            for c in (1, 2, 3):
                items[c].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            color = "#e8edf6"
            if i == len(rows) - 1:
                color = "#3ecf8e"
            elif delta < -0.005:
                color = "#ff6b6b"
            items[3].setForeground(QBrush(QColor("#ff6b6b" if i == len(rows) - 1 or delta < -0.005 else "#e8edf6")))
            if i == len(rows) - 1:
                for it in items:
                    fnt = it.font(); fnt.setBold(True); it.setFont(fnt)
            for c, it in enumerate(items):
                self.table.setItem(i, c, it)

        self._save_config(s)

    # ---------------- сохранение ----------------
    def _load_config(self):
        try:
            with open(config_path(), encoding="utf-8") as fh:
                st = json.load(fh)
        except Exception:
            st = {}
        from datetime import date as _date
        d = dict(self.DEFAULTS, month=_date.today().month - 1)
        d.update(st or {})
        self._updating = True
        self.salary.setValue(d["salary"]); self.bonus_pct.setValue(d["bonusPct"])
        self.harm_per_day.setValue(d["harmPerDay"]); self.harm_fixed.setChecked(d["harmFixed"])
        self.year.setValue(d["year"])
        self.month.setCurrentIndex(int(d["month"]))
        self.otg.setValue(d["otg"]); self.sick.setValue(d["sick"]); self.extra.setValue(d["extraDeduct"])
        idx = self.wd_sel.findData(d["workdaysSel"]);  self.wd_sel.setCurrentIndex(max(0, idx))
        self.wd_manual.setValue(d["workdaysManual"])
        self.adv_share.setValue(d["advShare"]); self.ndfl.setValue(d["ndfl"])
        self._updating = False

    def _save_config(self, s):
        try:
            with open(config_path(), "w", encoding="utf-8") as fh:
                json.dump(s, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PayCalc")
    w = PayCalc()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
