@echo off
chcp 932 > nul
setlocal

REM ============================================================
REM organize_by_date.bat
REM 写真・動画を撮影日時の「YYYY年MM月」フォルダへ自動整理する
REM ============================================================

REM このバッチファイルがある場所を基準に Python スクリプトを探す
set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%organize_by_date.py

REM Python スクリプトの存在確認
if not exist "%SCRIPT%" (
    echo エラー: スクリプトが見つかりません: %SCRIPT%
    pause
    exit /b 1
)

REM --- 引数なしで実行した場合のメニュー ---
if "%~1"=="" (
    echo ============================================================
    echo  写真・動画 日付別フォルダ整理ツール
    echo ============================================================
    echo.
    echo  使い方:
    echo    1. このバッチをダブルクリック → フォルダパスを入力
    echo    2. ドラッグ＆ドロップ → そのフォルダを整理
    echo    3. コマンドライン引数でパス指定
    echo.
    echo  オプション:
    echo    --dry-run  実際には移動せず確認のみ行う
    echo.
    echo ============================================================
    echo.

    REM ドライランするか選択
    set /p DRYRUN="ドライラン（確認のみ）で実行しますか？ [y/N]: "
    if /i "%DRYRUN%"=="y" (
        python "%SCRIPT%" --dry-run
    ) else (
        python "%SCRIPT%"
    )
    goto END
)

REM --- 引数ありで実行した場合 ---
REM 第1引数をフォルダパスとして使用
REM 第2引数に --dry-run が指定されていれば付与
if "%~2"=="--dry-run" (
    python "%SCRIPT%" "%~1" --dry-run
) else (
    python "%SCRIPT%" "%~1"
)

:END
echo.
pause
endlocal
