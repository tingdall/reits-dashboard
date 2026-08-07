@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem === 解除 Windows Mark of the Web 标记（浏览器下载文件的「区标识」）===
rem 现象：双击运行此 bat 时弹出「Internet 安全设置阻止打开一个或多个文件」
rem 解决：从本 bat 所在目录自动清除 :Zone.Identifier 备用数据流（含本 bat 与同目录 py）
for %%F in ("%~f0", "%~dp0reits_update.py") do (
  if exist "%%F:Zone.Identifier" (
    >nul 2>&1 del /ah "%%F:Zone.Identifier"
  )
)
rem 兜底：用 PowerShell Unblock-File（更彻底）
>nul 2>&1 powershell -NoProfile -Command "Try { Get-ChildItem -Path '%~dp0' -Include '*.bat','*.py' -File -ErrorAction SilentlyContinue | ForEach-Object { Unblock-File -Path $_.FullName -ErrorAction SilentlyContinue } } Catch {}"

echo ============================================
echo  机构间REITs（持有型不动产）数据更新
echo ============================================
echo.
echo [0/2] 正在查找 Python 解释器...
set "PYTHON="

rem 1) 优先使用 py 启动器（Python官方安装器自带）
where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py -3"

rem 2) 其次使用 PATH 中的 python
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON=python"
)

rem 3) 其次使用 PATH 中的 python3（部分环境区分 python2/python3）
if not defined PYTHON (
  where python3 >nul 2>nul
  if not errorlevel 1 set "PYTHON=python3"
)

if not defined PYTHON (
  echo.
  echo [错误] 未找到 Python。请任选其一：
  echo   a. 安装 Python 3 并勾选 "Add to PATH"（下载: https://www.python.org/downloads/）
  echo   b. 直接把 python.exe 放到本目录
  echo   c. 若此 bat 是从浏览器下载的：右键 - 属性 - 勾选「解除锁定」- 确定 - 再双击
  pause
  exit /b 1
)

echo      使用: %PYTHON%
echo.
echo [1/2] 正在抓取上交所+深交所最新数据...
%PYTHON% reits_update.py
if errorlevel 1 (
  echo.
  echo [错误] 更新失败，请检查网络后重试。
  echo   若提示 Internet 安全设置，请右键 - 属性 - 勾选「解除锁定」。
  pause
  exit /b 1
)
echo.
echo ============================================
echo  更新完成！请刷新看板网页加载最新数据。
echo ============================================
pause
