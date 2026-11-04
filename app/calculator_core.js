"use strict";

/* ============================================================
   ЯДРО КАЛЬКУЛЯТОРА — без обращения к DOM.
   Python-эквивалент: app/calculator_core.py (используется в
   десктопном приложении paycalc.py). Обе версии дают одинаковый
   результат — сверяется тестом tests/test_core_parity.py
   ============================================================ */

/* ---------- производственный календарь РФ (пятидневка, упрощённо) ---------- */
const HOLIDAYS = { // нерабочие праздничные дни, ст. 112 ТК РФ
  2024:["01-01","01-02","01-03","01-04","01-05","01-06","01-07","01-08","02-23","03-08","05-01","05-09","06-12","11-04"],
  2025:["01-01","01-02","01-03","01-04","01-05","01-06","01-07","01-08","02-23","03-08","05-01","05-09","06-12","11-04"],
  2026:["01-01","01-02","01-03","01-04","01-05","01-06","01-07","01-08","02-23","03-08","05-01","05-09","06-12","11-04"],
  2027:["01-01","01-02","01-03","01-04","01-05","01-06","01-07","01-08","02-23","03-08","05-01","05-09","06-12","11-04"]
};

function workdaysInMonth(year, monthIdx){
  const hol = new Set(HOLIDAYS[year] || []);
  const last = new Date(year, monthIdx+1, 0).getDate();
  let n = 0;
  for(let day=1; day<=last; day++){
    const wd = new Date(year, monthIdx, day).getDay();
    const key = String(monthIdx+1).padStart(2,"0") + "-" + String(day).padStart(2,"0");
    if(wd!==0 && wd!==6 && !hol.has(key)) n++;
  }
  return n;
}

const MONTHS = ["Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"];

/* надбавка за вредность по расчётным листам: авг 1896 ₽ / 14 дн, сен 3005 ₽ / 22 дн */
const HARM_BY_PAYSLIP = (1896 + 3005) / (14 + 22); // ≈ 136.01 ₽/день

/* ---------- основной расчёт ---------- */
function computePay(s){
  const oklad   = +s.salary || 0;
  const bPct    = (+s.bonusPct || 0)/100;
  const harmPd  = +s.harmPerDay || 0;
  const harmFix = !!s.harmFixed;
  const WD      = s.workdaysSel === "manual"
                    ? Math.max(1, +s.workdaysManual || 1)
                    : workdaysInMonth(+s.year, +s.month);
  const otg     = Math.max(0, +s.otg || 0);
  const sick    = Math.max(0, +s.sick || 0);
  const extra   = +s.extraDeduct || 0;
  const advSh   = Math.min(Math.max((+s.advShare || 0)/100, 0), 1);
  const ndfl    = Math.min(Math.max((+s.ndfl || 0)/100, 0), 1);

  const absent = Math.min(otg + sick, WD);
  const worked = Math.max(WD - absent, 0);

  /* стоимость одного дня отсутствия (на руки) */
  const okladDay   = oklad / WD;
  const bonusDay   = okladDay * bPct;
  const harmDayEff = harmFix ? 0 : harmPd;   // фиксированная вредность от отгулов не уменьшается
  const grossDay   = okladDay + bonusDay + harmDayEff;
  const netDay     = grossDay * (1 - ndfl);

  /* сценарии: факт и «без отгулов» */
  function scenario(daysWorked, extraAmt){
    const okladGross = oklad * (daysWorked/WD);
    const bonusGross = okladGross * bPct;
    const harmFinal  = harmFix ? (daysWorked>0 ? harmPd*WD : 0) : harmPd*daysWorked;
    const gross = okladGross + bonusGross + harmFinal - extraAmt;
    const tax   = Math.max(gross,0) * ndfl;
    const net   = Math.max(gross,0) - tax;
    const salGross = okladGross*(1-advSh) + harmFinal - extraAmt;
    const salNet   = Math.max(salGross - tax, 0);
    const advNet   = net - salNet;   // остаток условно показываем как аванс 20 числа
    return {okladGross, bonusGross, harm:harmFinal, gross, tax, net, advNet, salNet};
  }
  const P  = scenario(worked, extra);
  const PF = scenario(WD, 0);
  const loss = PF.net - P.net;

  const rows = [
    ["Оклад (" + worked + " из " + WD + " дн.)", PF.okladGross, P.okladGross],
    ["Премия " + (+s.bonusPct || 0) + "%", PF.bonusGross, P.bonusGross],
    ["Надбавка за вредность" + (harmFix ? " (фикс.)" : " (" + worked + " дн.)"), PF.harm, P.harm],
    ["Доп. вычеты", 0, -extra],
    ["НДФЛ " + (ndfl*100) + "%", -PF.tax, -P.tax],
  ];

  return {
    WD, absent, worked,
    okladDay, bonusDay, harmDay: harmDayEff, taxBack: grossDay*ndfl, costPerDay: netDay,
    net: P.net, loss, netNoLoss: PF.net, advNet: P.advNet, salNet: P.salNet,
    pfAdvNet: PF.advNet, pfSalNet: PF.salNet,
    rows
  };
}

if (typeof module !== "undefined" && module.exports) module.exports = { computePay, workdaysInMonth, MONTHS, HARM_BY_PAYSLIP };
