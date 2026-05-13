#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_MD = ROOT / "信息论复习题满分复习文档.md"
OUTPUT_HTML = ROOT / "信息论复习题整理版.html"
STYLE_HEADER = ROOT / "review_style.html"


PROSE_BLOCKS = {
    20,
    38,
    55,
    58,
    64,
    65,
    89,
    107,
    108,
    117,
    120,
    123,
    126,
    127,
    128,
    129,
    130,
    131,
    132,
    133,
    134,
    135,
    136,
}

ANSWER_BLOCKS = {
    8,
    16,
    114,
    116,
    118,
    121,
    122,
    125,
}

LITERAL_BLOCKS = {
    2,
    3,
    5,
    30,
    32,
    60,
    66,
    67,
    69,
    73,
    74,
    78,
    80,
    97,
    101,
    109,
    110,
    111,
    138,
    139,
    140,
    141,
    142,
    143,
    144,
    145,
    146,
    137,
}

CUSTOM_LATEX_BLOCKS = {
    21: r"""
\begin{aligned}
P(a_1) &= 0.5,\quad P(a_2) = 0.5 \\
P(Y \mid X) &=
\left[
\begin{array}{cc}
0.6 & 0.4 \\
0.2 & 0.8
\end{array}
\right]
\end{aligned}
""".strip(),
    33: r"""
P =
\begin{bmatrix}
0.6 & 0.4 & 0   & 0 \\
0   & 0   & 0.5 & 0.5 \\
0.5 & 0.5 & 0   & 0 \\
0   & 0   & 0.4 & 0.6
\end{bmatrix}
""".strip(),
    45: r"""
P =
\begin{bmatrix}
0.7 & 0.3 \\
0.4 & 0.6
\end{bmatrix}
""".strip(),
    81: r"G = \left[ I_k \mid P \right]".strip(),
    82: r"H = \left[ P^{T} \mid I_{n-k} \right]".strip(),
    90: r"""
G =
\begin{bmatrix}
1 & 0 & 0 & 1 & 1 & 0 \\
0 & 1 & 0 & 0 & 1 & 1 \\
0 & 0 & 1 & 1 & 0 & 1
\end{bmatrix}
""".strip(),
    92: r"""
P =
\begin{bmatrix}
1 & 1 & 0 \\
0 & 1 & 1 \\
1 & 0 & 1
\end{bmatrix}
""".strip(),
    93: r"""
\begin{aligned}
H &= \left[ P^{T} \mid I_3 \right] \\
  &=
\begin{bmatrix}
1 & 0 & 1 & 1 & 0 & 0 \\
1 & 1 & 0 & 0 & 1 & 0 \\
0 & 1 & 1 & 0 & 0 & 1
\end{bmatrix}
\end{aligned}
""".strip(),
    124: r"""
\begin{aligned}
R(D_{\min}) &= H(X) \\
R(D_{\max}) &= 0
\end{aligned}
""".strip(),
}


def render_note_block(text: str, kind: str) -> str:
    return (
        f"::: {{.{kind}}}\n\n"
        f"{text.strip()}\n\n"
        ":::\n"
    )


def render_literal_block(text: str) -> str:
    return (
        "::: {.literal-block}\n\n"
        "```text\n"
        f"{text.strip()}\n"
        "```\n\n"
        ":::\n"
    )


def make_math_block(latex: str) -> str:
    return (
        "::: {.formula-block}\n\n"
        "$$\n"
        f"{latex.strip()}\n"
        "$$\n\n"
        ":::\n"
    )


def normalize_symbols(expr: str) -> str:
    expr = expr.strip()
    expr = expr.replace("∞", r"\infty")
    expr = expr.replace("≈", r"\approx")
    expr = expr.replace("<=", r"\le ")
    expr = expr.replace(">=", r"\ge ")
    expr = expr.replace("->", r"\to ")
    expr = expr.replace("...", r"\cdots")
    expr = expr.replace("–", "-")
    expr = expr.replace("—", "-")
    expr = expr.replace("%", r"\%")

    replacements = {
        "H_infinity": r"H_{\infty}",
        "d_min": r"d_{\min}",
        "D_min": r"D_{\min}",
        "D_max": r"D_{\max}",
        "Dmin": r"D_{\min}",
        "Dmax": r"D_{\max}",
        "K_bar": r"\bar{K}",
        "pi_F": r"\pi_F",
        "pi_D": r"\pi_D",
        "P^T": r"P^{T}",
        "H^T": r"H^{T}",
        "X^N": r"X^{N}",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)

    expr = re.sub(r"\bpi\b", r"\\pi", expr)
    expr = re.sub(r"\bsum_(\w+)", r"\\sum_{\1}", expr)
    expr = expr.replace("max_{", r"\operatorname{max}_{")
    expr = re.sub(r"\bmin\{([^}]*)\}", r"\\min\\{\1\\}", expr)
    expr = re.sub(r"\bmax\{([^}]*)\}", r"\\max\\{\1\\}", expr)
    expr = re.sub(r"floor\(([^()]*(?:\([^)]*\)[^()]*)*)\)", r"\\lfloor \1 \\rfloor", expr)
    expr = re.sub(r"(?<=[0-9A-Za-z\)])\|(?=[0-9A-Za-z\(])", r"\\mid ", expr)
    expr = re.sub(r"(?<=\d)log", r" \\log", expr)
    expr = re.sub(r"(?<=\))log", r" \\log", expr)
    expr = re.sub(r"\blog\b", r"\\log", expr)
    expr = re.sub(r"\\log(?=[0-9(])", r"\\log ", expr)
    expr = re.sub(r"(?<=[0-9A-Za-z\)])\*(?=[0-9A-Za-z\(])", r" \\cdot ", expr)

    for prefix in ("a", "b", "w", "S", "N", "M", "B", "G", "x"):
        expr = re.sub(rf"\b{prefix}(\d+)\b", rf"{prefix}_{{\1}}", expr)

    expr = expr.replace("bit/symbol", r"\text{bit/symbol}")
    expr = expr.replace(" bit", r" \text{bit}")
    expr = expr.replace("eta", r"\eta")
    expr = expr.replace("GF(2)", r"\mathrm{GF}(2)")
    expr = expr.replace("I_k", r"I_k")
    expr = expr.replace("I_3", r"I_3")
    expr = re.sub(r"(?<=\d)\s*/\s*(?=\d)", "/", expr)
    expr = re.sub(r"\s+", " ", expr).strip()

    if expr.startswith("or "):
        expr = r"\text{or } " + expr[3:]
    return expr


def split_compound_lines(text: str) -> list[str]:
    raw_lines = [line.rstrip() for line in text.strip().splitlines()]
    lines: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if "  " in line and not any(token in line for token in ("[", "]", "->")):
            pieces = [piece.strip() for piece in re.split(r"\s{2,}", line) if piece.strip()]
            if len(pieces) > 1 and all(len(piece) < 80 for piece in pieces):
                lines.extend(pieces)
                continue

        lines.append(stripped)
    return lines


def latex_line(expr: str) -> str:
    expr = normalize_symbols(expr)
    if expr.startswith((r"\begin{", r"\left[")):
        return expr

    operator_match = re.match(r"^(.*?)(\\approx|\\le|\\ge|=)(.*)$", expr)
    if operator_match:
        left, operator, right = operator_match.groups()
        left = left.strip()
        right = right.strip()
        if left:
            return f"{left} &{operator} {right}"
        return f"&{operator} {right}"
    return expr


def convert_formula_block(text: str) -> str:
    lines = split_compound_lines(text)
    if not lines:
        return render_literal_block(text)

    if len(lines) == 1:
        return make_math_block(normalize_symbols(lines[0]))

    aligned = " \\\\\n".join(latex_line(line) for line in lines)
    return make_math_block(rf"\begin{{aligned}}{aligned}\end{{aligned}}")


def transform_markdown(source: str) -> str:
    counter = {"value": 0}

    def replace(match: re.Match[str]) -> str:
        counter["value"] += 1
        idx = counter["value"]
        content = match.group(1)

        if idx in CUSTOM_LATEX_BLOCKS:
            return make_math_block(CUSTOM_LATEX_BLOCKS[idx])
        if idx in PROSE_BLOCKS:
            return render_note_block(content, "note-block")
        if idx in ANSWER_BLOCKS:
            return render_note_block(content, "answer-block")
        if idx in LITERAL_BLOCKS:
            return render_literal_block(content)
        return convert_formula_block(content)

    processed = re.sub(r"```(?:\w+)?\n(.*?)```", replace, source, flags=re.S)

    preface = (
        "> 本页依据 `信息论复习题满分复习文档.docx` 与 `复习题-2026 2.docx` 整理，"
        "主内容采用整理稿，并将可识别的公式统一规范为数学排版。\n\n"
    )
    return preface + processed


def build_html(markdown_text: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as temp_md:
        temp_md.write(markdown_text)
        temp_md_path = Path(temp_md.name)

    cmd = [
        "pandoc",
        str(temp_md_path),
        "--standalone",
        "--toc",
        "--toc-depth=3",
        "--mathml",
        "--metadata",
        "title=信息论复习题整理版",
        "--include-in-header",
        str(STYLE_HEADER),
        "-o",
        str(OUTPUT_HTML),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    source = SOURCE_MD.read_text(encoding="utf-8")
    processed = transform_markdown(source)
    build_html(processed)


if __name__ == "__main__":
    main()
