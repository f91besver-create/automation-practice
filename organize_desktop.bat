@echo off
chcp 65001 > nul
setlocal

echo ============================================================
echo  フォルダ整理ツール
echo ============================================================
echo.
echo 整理するフォルダのパスを入力してください。
echo （Enterのみで省略するとデスクトップを対象にします）
echo.
set /p TARGET_PATH="パス: "

if "%TARGET_PATH%"=="" (
    set TARGET_ARGS=
    echo.
    echo → デスクトップを対象にします。
) else (
    set TARGET_ARGS="%TARGET_PATH%"
    echo.
    echo → 対象: %TARGET_PATH%
)

echo.
echo ■ ドライラン実行中（実際には移動しません）...
echo.

python "%~dp0organize_desktop.py" %TARGET_ARGS% --dry-run
if errorlevel 1 (
    echo.
    echo [エラー] スクリプトの実行に失敗しました。
    echo Python がインストールされているか確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  上記の内容でファイルを移動します。
echo  続行しますか？
echo ============================================================
echo.
choice /c YN /m "実行する場合は Y、キャンセルは N を押してください"

if errorlevel 2 (
    echo.
    echo キャンセルしました。
    pause
    exit /b 0
)

echo.
echo ■ 本番実行中...
echo.

python "%~dp0organize_desktop.py" %TARGET_ARGS%

echo.
echo ============================================================
echo  処理が完了しました。
echo ============================================================
pause
