@echo off
rem ============================================================
rem  Установка «Калькулятора зарплаты» как приложения Windows
rem  1) ставит Python (если нет) и PySide6
rem  2) создаёт ярлык на рабочем столе + в меню Пуск
rem  Запускать двойным кликом.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python не найден. Открываю страницу загрузки Python...
    start https://www.python.org/downloads/
    echo Установите Python, поставив галочку "Add python.exe to PATH",
    echo затем запустите этот файл ещё раз.
    pause
    exit /b 1
)

echo Устанавливаю библиотеку интерфейса (PySide6)...
python -m pip install --quiet --upgrade PySide6 || (
    echo Не удалось установить PySide6. Попробуйте: python -m pip install PySide6
    pause
    exit /b 1
)

echo Создаю ярлыки...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$targets = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('StartMenu'));" ^
  "foreach ($t in $targets) {" ^
  "  $lnk = $ws.CreateShortcut((Join-Path $t 'Калькулятор зарплаты.lnk'));" ^
  "  $lnk.TargetPath = '%~dp0run_paycalc.vbs';" ^
  "  $lnk.WorkingDirectory = '%~dp0';" ^
  "  $lnk.IconLocation = 'shell32.dll,265';" ^
  "  $lnk.Description = 'Калькулятор зарплаты с отгулами';" ^
  "  $lnk.Save();" ^
  "}"

echo Готово! Ищите «Калькулятор зарплаты» на рабочем столе или в меню Пуск.
pause
