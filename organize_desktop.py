"""
organize_desktop.py
デスクトップのファイルを拡張子ごとにフォルダへ自動整理するスクリプト
"""

import os
import shutil
from pathlib import Path

# ===== 設定 =====

# 整理対象のデスクトップパス（自動取得）
DESKTOP = Path.home() / "Desktop"

# 拡張子 → フォルダ名のマッピング
EXTENSION_MAP = {
    # 画像
    ".jpg": "画像",
    ".jpeg": "画像",
    ".png": "画像",
    ".gif": "画像",
    ".bmp": "画像",
    ".svg": "画像",
    ".webp": "画像",
    ".ico": "画像",
    # 動画
    ".mp4": "動画",
    ".mov": "動画",
    ".avi": "動画",
    ".mkv": "動画",
    ".wmv": "動画",
    ".flv": "動画",
    # 音楽
    ".mp3": "音楽",
    ".wav": "音楽",
    ".flac": "音楽",
    ".aac": "音楽",
    ".ogg": "音楽",
    # ドキュメント
    ".pdf": "ドキュメント",
    ".doc": "ドキュメント",
    ".docx": "ドキュメント",
    ".xls": "ドキュメント",
    ".xlsx": "ドキュメント",
    ".ppt": "ドキュメント",
    ".pptx": "ドキュメント",
    ".txt": "ドキュメント",
    ".md": "ドキュメント",
    ".csv": "ドキュメント",
    # 圧縮ファイル
    ".zip": "圧縮ファイル",
    ".rar": "圧縮ファイル",
    ".7z": "圧縮ファイル",
    ".tar": "圧縮ファイル",
    ".gz": "圧縮ファイル",
    # プログラム・スクリプト
    ".py": "プログラム",
    ".js": "プログラム",
    ".ts": "プログラム",
    ".html": "プログラム",
    ".css": "プログラム",
    ".json": "プログラム",
    ".xml": "プログラム",
    ".sh": "プログラム",
    ".bat": "プログラム",
    # 実行ファイル・インストーラー
    ".exe": "実行ファイル",
    ".msi": "実行ファイル",
    ".dmg": "実行ファイル",
    ".pkg": "実行ファイル",
}

# マッピングにない拡張子のファイルを入れるフォルダ名
OTHER_FOLDER = "その他"


# ===== メイン処理 =====

def organize_desktop(dry_run: bool = False) -> None:
    """
    デスクトップのファイルを拡張子ごとにフォルダへ移動する。

    Args:
        dry_run: True にすると実際には移動せず、移動予定の内容だけ表示する
    """

    if not DESKTOP.exists():
        print(f"デスクトップが見つかりません: {DESKTOP}")
        return

    mode_label = "[DRY RUN] " if dry_run else ""
    print(f"{mode_label}整理対象: {DESKTOP}\n")

    moved = 0       # 移動したファイル数
    skipped = 0     # スキップしたファイル数

    # デスクトップ直下のアイテムを走査
    for item in sorted(DESKTOP.iterdir()):
        # フォルダはスキップ（整理済みフォルダを再帰処理しない）
        if item.is_dir():
            continue

        # ショートカット（.lnk）はスキップ
        if item.suffix.lower() == ".lnk":
            skipped += 1
            print(f"  スキップ: {item.name}（ショートカット）")
            continue

        # 移動先フォルダを決定（マッピングにない場合は「その他」）
        ext = item.suffix.lower()
        folder_name = EXTENSION_MAP.get(ext, OTHER_FOLDER)
        dest_dir = DESKTOP / folder_name

        # 移動先に同名ファイルが存在する場合はリネームして衝突を回避
        dest_file = dest_dir / item.name
        if dest_file.exists():
            stem = item.stem
            suffix = item.suffix
            counter = 1
            while dest_file.exists():
                dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        print(f"  {mode_label}{item.name}  →  {folder_name}/{dest_file.name}")

        if not dry_run:
            # フォルダが存在しない場合は作成
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest_file))

        moved += 1

    # 結果サマリー
    print(f"\n{'─' * 40}")
    if dry_run:
        print(f"[DRY RUN] 移動予定: {moved} ファイル、スキップ: {skipped} ファイル")
        print("実際に移動するには dry_run=False で実行してください。")
    else:
        print(f"完了: {moved} ファイルを移動、{skipped} ファイルをスキップ")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="デスクトップのファイルを拡張子ごとにフォルダ整理します。"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には移動せず、移動予定の内容だけ表示する",
    )
    args = parser.parse_args()

    organize_desktop(dry_run=args.dry_run)
