#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_MD = ROOT / "信息论题目答案中英对照.md"
STYLE_HEADER = ROOT / "qa_bilingual_style.html"
OUTPUT_HTML = ROOT / "信息论题目答案中英对照.html"


def main() -> None:
    cmd = [
        "pandoc",
        str(SOURCE_MD),
        "--standalone",
        "--toc",
        "--toc-depth=3",
        "--mathml",
        "--metadata",
        "title=信息论题目答案中英对照",
        "--include-in-header",
        str(STYLE_HEADER),
        "-o",
        str(OUTPUT_HTML),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
