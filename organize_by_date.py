"""
organize_by_date.py
写真・動画ファイルを撮影日時ごとに「YYYY年MM月」フォルダへ自動整理するスクリプト

日時の取得順:
  1. EXIFデータの撮影日時 (DateTimeOriginal)
  2. EXIFデータの最初の記録日時 (DateTime)
  3. ファイルの更新日時 (mtime)
"""

import os
import shutil
import struct
import argparse
from pathlib import Path
from datetime import datetime

# ===== 設定 =====

# EXIFを読む対象の拡張子（画像）
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tiff", ".tif", ".heic", ".heif", ".webp"}

# 日時フォルダへ整理する対象の拡張子（画像 + 動画）
TARGET_EXTENSIONS = IMAGE_EXTENSIONS | {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v", ".3gp",
    ".png", ".gif", ".bmp", ".raw", ".cr2", ".nef", ".arw", ".dng",
}


# ===== EXIF 読み取り =====

def _read_exif_date(path: Path) -> datetime | None:
    """
    EXIFデータから撮影日時を取得する。
    外部ライブラリ不要の純粋な実装。
    取得できない場合は None を返す。
    """
    # EXIFを持つ可能性があるのはJPEG/TIFF/HEICなど
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return None

    try:
        with open(path, "rb") as f:
            data = f.read(65536)  # 先頭64KBだけ読めば十分

        # --- JPEG の場合 ---
        if data[:2] == b"\xff\xd8":
            return _parse_jpeg_exif(data)

        # --- TIFF の場合 ---
        if data[:2] in (b"II", b"MM"):
            return _parse_tiff_exif(data)

    except Exception:
        pass  # 読み取り失敗は無視してフォールバックへ

    return None


def _parse_jpeg_exif(data: bytes) -> datetime | None:
    """JPEG バイナリから APP1 (EXIF) セグメントを探して日時を抽出する。"""
    i = 2  # SOI マーカーの次から開始
    while i + 4 <= len(data):
        # マーカーを読む
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xD9:  # EOI
            break
        if marker in (0xD8, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7):
            # サイズフィールドのないマーカー
            i += 2
            continue

        if i + 4 > len(data):
            break
        seg_len = struct.unpack(">H", data[i + 2: i + 4])[0]
        seg_end = i + 2 + seg_len

        if marker == 0xE1 and data[i + 4: i + 10] == b"Exif\x00\x00":
            # APP1 セグメント = EXIF データ
            tiff_start = i + 10
            tiff_data = data[tiff_start:seg_end]
            return _parse_tiff_exif(tiff_data)

        i = seg_end

    return None


def _parse_tiff_exif(data: bytes) -> datetime | None:
    """TIFF 形式の EXIF バイナリから撮影日時タグを探す。"""
    if len(data) < 8:
        return None

    # バイトオーダーの確認
    if data[:2] == b"II":
        endian = "<"  # リトルエンディアン
    elif data[:2] == b"MM":
        endian = ">"  # ビッグエンディアン
    else:
        return None

    # IFD0 のオフセットを取得
    ifd0_offset = struct.unpack(endian + "I", data[4:8])[0]

    # IFD0 と ExifIFD の両方を探す
    # タグID: 0x9003 = DateTimeOriginal, 0x0132 = DateTime, 0x8769 = ExifIFD
    date_tags = {0x9003: None, 0x0132: None}
    exif_ifd_offset = None

    def read_ifd(offset: int) -> None:
        nonlocal exif_ifd_offset
        if offset + 2 > len(data):
            return
        count = struct.unpack(endian + "H", data[offset: offset + 2])[0]
        for j in range(count):
            entry_start = offset + 2 + j * 12
            if entry_start + 12 > len(data):
                break
            tag = struct.unpack(endian + "H", data[entry_start: entry_start + 2])[0]
            type_ = struct.unpack(endian + "H", data[entry_start + 2: entry_start + 4])[0]
            n = struct.unpack(endian + "I", data[entry_start + 4: entry_start + 8])[0]
            val_raw = data[entry_start + 8: entry_start + 12]

            if tag in date_tags:
                # ASCII 文字列タグ (type=2)
                if type_ == 2:
                    str_len = n
                    if str_len <= 4:
                        str_data = val_raw[:str_len]
                    else:
                        str_offset = struct.unpack(endian + "I", val_raw)[0]
                        str_data = data[str_offset: str_offset + str_len]
                    date_tags[tag] = str_data.rstrip(b"\x00").decode("ascii", errors="ignore")

            elif tag == 0x8769:
                # ExifIFD へのポインタ
                exif_ifd_offset = struct.unpack(endian + "I", val_raw)[0]

    read_ifd(ifd0_offset)

    # ExifIFD も読む（DateTimeOriginal はここにあることが多い）
    if exif_ifd_offset:
        read_ifd(exif_ifd_offset)

    # DateTimeOriginal → DateTime の優先順で返す
    for tag_id in (0x9003, 0x0132):
        raw = date_tags.get(tag_id)
        if raw:
            dt = _parse_exif_datetime_str(raw)
            if dt:
                return dt

    return None


def _parse_exif_datetime_str(s: str) -> datetime | None:
    """'YYYY:MM:DD HH:MM:SS' 形式の EXIF 日時文字列を datetime に変換する。"""
    try:
        return datetime.strptime(s.strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


# ===== 日時取得（EXIF → mtime フォールバック） =====

def get_datetime(path: Path) -> tuple[datetime, str]:
    """
    ファイルの撮影日時を返す。
    取得元を示す文字列も合わせて返す（ログ表示用）。

    Returns:
        (datetime, source_label)
        source_label: "EXIF" または "更新日時"
    """
    dt = _read_exif_date(path)
    if dt is not None:
        return dt, "EXIF"

    # フォールバック: ファイルの更新日時
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime), "更新日時"


# ===== メイン処理 =====

def organize_by_date(target: Path, dry_run: bool = False) -> None:
    """
    指定フォルダの写真・動画を撮影日時の「YYYY年MM月」フォルダへ移動する。

    Args:
        target:  整理対象のフォルダパス
        dry_run: True にすると実際には移動せず、移動予定の内容だけ表示する
    """

    if not target.exists():
        print(f"フォルダが見つかりません: {target}")
        return

    if not target.is_dir():
        print(f"フォルダではありません: {target}")
        return

    mode_label = "[DRY RUN] " if dry_run else ""
    print(f"{mode_label}整理対象: {target}\n")

    moved = 0    # 移動したファイル数
    skipped = 0  # スキップしたファイル数

    # 対象フォルダ直下のファイルを走査（サブフォルダは処理しない）
    for item in sorted(target.iterdir()):
        if item.is_dir():
            continue  # フォルダはスキップ

        ext = item.suffix.lower()
        if ext not in TARGET_EXTENSIONS:
            skipped += 1
            print(f"  スキップ: {item.name}（対象外の拡張子）")
            continue

        # 撮影日時を取得
        dt, source = get_datetime(item)

        # フォルダ名を「YYYY年MM月」形式で生成
        folder_name = dt.strftime("%Y年%m月%d日")
        dest_dir = target / folder_name

        # 同名ファイルが存在する場合は連番を付けて衝突を回避
        dest_file = dest_dir / item.name
        if dest_file.exists():
            stem = item.stem
            suffix = item.suffix
            counter = 1
            while dest_file.exists():
                dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        print(f"  {mode_label}{item.name}  →  {folder_name}/{dest_file.name}  [{source}]")

        if not dry_run:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest_file))

        moved += 1

    # 結果サマリー
    print(f"\n{'─' * 40}")
    if dry_run:
        print(f"[DRY RUN] 移動予定: {moved} ファイル、スキップ: {skipped} ファイル")
        print("実際に移動するには --dry-run を外して実行してください。")
    else:
        print(f"完了: {moved} ファイルを移動、{skipped} ファイルをスキップ")


# ===== エントリーポイント =====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="写真・動画を撮影日時の「YYYY年MM月」フォルダへ自動整理します。"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="整理対象のフォルダパス（省略時は実行時に入力を求めます）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には移動せず、移動予定の内容だけ表示する",
    )
    args = parser.parse_args()

    # フォルダパスが引数で指定されていない場合は入力を求める
    if args.path:
        target = Path(args.path)
    else:
        raw = input("整理対象のフォルダパスを入力してください: ").strip().strip('"')
        target = Path(raw)

    organize_by_date(target=target, dry_run=args.dry_run)
