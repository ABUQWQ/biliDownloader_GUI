#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本号同步脚本：以 git tag 为唯一版本来源，同步更新项目内所有版本声明。

用法：
    python make/sync_version.py V1.8.2 [--date 2026/08/26]

同步目标：
    - etc/__init__.py   -> Release_INFO = ["x.y.z", "yyyy/mm/dd"]
    - win32setup.nsi    -> !define PRODUCT_VERSION "x.y.z"（字节级替换，保护 GBK 编码）

另会校验 MIGRATION.md 是否包含对应版本章节，缺失时打印警告。
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG_PATTERN = re.compile(r"^V?(\d+\.\d+\.\d+)$")


def sync_release_info(version: str, date: str) -> None:
    target = ROOT / "etc" / "__init__.py"
    text = target.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'Release_INFO\s*=\s*\["[^"]+",\s*"[^"]+"\]',
        'Release_INFO = ["' + version + '", "' + date + '"]',
        text,
    )
    if count != 1:
        raise RuntimeError(str(target) + ": 未找到唯一的 Release_INFO 声明，已中止")
    target.write_text(new_text, encoding="utf-8")
    print('[OK] etc/__init__.py -> Release_INFO = ["' + version + '", "' + date + '"]')


def sync_nsi(version: str) -> None:
    target = ROOT / "win32setup.nsi"
    data = target.read_bytes()
    new_data, count = re.subn(
        rb'!define PRODUCT_VERSION "[^"]+"',
        ('!define PRODUCT_VERSION "' + version + '"').encode("ascii"),
        data,
    )
    if count != 1:
        raise RuntimeError(str(target) + ": 未找到唯一的 PRODUCT_VERSION 定义，已中止")
    target.write_bytes(new_data)
    print('[OK] win32setup.nsi -> PRODUCT_VERSION "' + version + '"')


def check_migration_notes(version: str) -> None:
    target = ROOT / "MIGRATION.md"
    if not target.exists():
        print("[WARN] 未找到 MIGRATION.md，跳过版本章节检查")
        return
    text = target.read_text(encoding="utf-8")
    if "V" + version not in text:
        print("[WARN] MIGRATION.md 中没有 V" + version + " 相关章节，请记得补充发版说明")


def main() -> int:
    parser = argparse.ArgumentParser(description="同步项目版本号与构建日期")
    parser.add_argument("tag", help="版本标签，如 V1.8.2 或 1.8.2")
    parser.add_argument(
        "--date",
        default=datetime.date.today().strftime("%Y/%m/%d"),
        help="构建日期，格式 yyyy/mm/dd，默认为今天",
    )
    args = parser.parse_args()

    match = TAG_PATTERN.match(args.tag)
    if not match:
        print("[ERROR] 非法版本标签: " + args.tag + "（期望形如 V1.8.2）", file=sys.stderr)
        return 1
    version = match.group(1)

    try:
        sync_release_info(version, args.date)
        sync_nsi(version)
    except RuntimeError as exc:
        print("[ERROR] " + str(exc), file=sys.stderr)
        return 1

    check_migration_notes(version)
    print("[DONE] 版本已同步为 " + version + "（构建日期 " + args.date + "）")
    return 0


if __name__ == "__main__":
    sys.exit(main())