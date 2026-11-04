"use strict";
/* Генерирует эталонные результаты JS-ядра для тех же кейсов, что и test_core_parity.py */
const path = require("path");
const { computePay } = require(path.join(__dirname, "..", "app", "calculator_core.js"));

const CASES = [];
for (const year of [2025, 2026])
  for (let month = 0; month < 12; month++)
    CASES.push({ year, month, otg: 3 });
CASES.push(
  { salary:79000, bonusPct:20, harmPerDay:136.01, harmFixed:false, year:2026, month:9,
    otg:0, sick:0, extraDeduct:0, workdaysSel:"auto", workdaysManual:22, advShare:50, ndfl:13 },
  { salary:79000, bonusPct:20, harmPerDay:136.01, harmFixed:true, year:2026, month:9,
    otg:4.5, sick:2, extraDeduct:1500, workdaysSel:"manual", workdaysManual:21, advShare:40, ndfl:13 },
  { salary:50000, bonusPct:0, harmPerDay:0, harmFixed:false, year:2026, month:0,
    otg:31, sick:0, extraDeduct:0, workdaysSel:"auto", workdaysManual:22, advShare:50, ndfl:13 }
);
const out = CASES.map(s => {
  const r = computePay(s);
  return { WD:r.WD, absent:r.absent, worked:r.worked, costPerDay:r.costPerDay,
           net:r.net, loss:r.loss, netNoLoss:r.netNoLoss, advNet:r.advNet, salNet:r.salNet };
});
process.stdout.write(JSON.stringify(out));
