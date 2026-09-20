#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_to_text.py — постоянный скрипт: ЛЮБОЙ HTML-код, полученный в результате
обработки данных из источника (описание события, блок 3), выводится в ДВУХ
вариантах:
  1) для копирования — HTML-код (вставляется в админку);
  2) для показа — текст с лёгкой разметкой (блок 2 прототипа).

Правило проекта (20.09.2026): текст для показа выводится ТОЛЬКО этим скриптом,
из финального HTML-фрагмента. Руками текст «рядом с HTML» НЕ пишем — это
единственный источник расхождений.

Вход: путь к файлу с HTML-фрагментом, либо HTML в стандартный ввод.
Скрипт универсален: корректно обрабатывает любой фрагмент описания события
(шапка <p class="small">…</p>, обычные <p>, <b>/<i>, &nbsp;, <br>,
<blockquote class="small">…</blockquote>, заглушку <KLBLOCK …/>).
Вариант «для показа» строится строго из HTML (слова, абзацы, ё,
кавычки-ёлочки, тире сохраняются как в HTML; nbsp → обычный пробел;
<b> → **, <i> → *, вложенные <b><i>…</i></b> → ***…***).

Использование:
    python -X utf8 tools/html_to_text.py <файл.html>
    python -X utf8 tools/html_to_text.py --stdin < прототип.html
    type прототип.html | python -X utf8 tools/html_to_text.py
"""
import sys
import re
import argparse


def _nbsp_to_space(html: str) -> str:
    """Все неразбиваемые пробелы и их HTML-энтити -> обычный пробел."""
    html = html.replace("&nbsp;", " ")
    html = html.replace("\u00a0", " ")
    html = html.replace("\u2009", " ")
    html = html.replace("\u202f", " ")
    return html


def _strip_tags_except_b_i(html: str) -> str:
    """Удаляем все теги, КРОМЕ <b> и <i> (их позже превратим в разметку)."""
    def _keep(m: re.Match) -> str:
        return m.group(0)
    # защищаем b/i, остальное снимаем
    html = re.sub(r"<(?!b\b|/?b\b|i\b|/?i\b)[^>]+>", "", html)
    return html


def _read_html_file(path: str) -> str:
    """Читает файл: сначала UTF-8; если символы не декодируются — Windows-1251."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, encoding="cp1251") as f:
            return f.read()


def _to_inner_html(html: str) -> str:
    """Вариант для копирования: убираем внешнюю обвязку div (itemblock/memo),
    оставляем внутренние блоки (шапка small, KLBLOCK, p, blockquote)."""
    html = re.sub(r"<div\s+class=[\"'][^\"']*itemblock[^\"']*[\"'][^>]*>", "", html)
    html = re.sub(r"<div\s+class=[\"'][^\"']*memo[^\"']*[\"'][^>]*>", "", html)
    html = re.sub(r"</div>", "", html)
    html = html.replace("\xa0", "\xa0")  # nbsp в HTML-варианте сохраняем
    return html.strip()


def _inline_to_markdown(html: str) -> str:
    """Внутренняя разметка: <b> -> **, <i> -> *, вложенные -> ***, nbsp->пробел."""
    html = _nbsp_to_space(html)
    html = re.sub(r"<br\s*/?>", "\n", html)
    # жирный курсив — вложенные
    html = re.sub(r"<b>\s*<i>(.*?)</i>\s*</b>", r"***\1***", html, flags=re.S)
    html = re.sub(r"<i>\s*<b>(.*?)</b>\s*</i>", r"***\1***", html, flags=re.S)
    # просто жирный и курсив
    html = re.sub(r"<b>(.*?)</b>", r"**\1**", html, flags=re.S)
    html = re.sub(r"<i>(.*?)</i>", r"*\1*", html, flags=re.S)
    # оставшиеся теги — снять (в т.ч. классы вроде class="small")
    html = re.sub(r"<[^>]+>", "", html)
    return html


def blockquote_class_small(inner: str) -> str:
    """Содержимое <blockquote class="small">: аннотационная цитата курсивом.
    Внутренние <p> разделяются пустой строкой."""
    inner = inner.strip()
    # каждый внутренний <p> — отдельным абзацем курсивом
    paras = re.split(r"</p>\s*<p", inner)
    out = []
    for p in paras:
        p = _inline_to_markdown(p)
        p = re.sub(r"[ \t]+", " ", p).strip()
        if p:
            out.append("*%s*" % p)
    return "\n\n".join(out)


def convert(html: str) -> tuple:
    """Главная функция: HTML-фрагмент -> (HTML_для_копирования, текст_для_показа)."""
    inner_html = _to_inner_html(html)

    # ---------- вариант 1: HTML для копирования ----------
    copy_html = inner_html

    # ---------- вариант 2: текст для показа ----------
    # обрабатываем по частям: KLBLOCK-заглушку оставляем меткой,
    # blockquote.small — курсивом, остальное — обычными абзацами.
    tokens = re.split(r"(<KLBLOCK\s+[^>]*/>)", inner_html)
    parts = []
    for tok in tokens:
        if tok.startswith("<KLBLOCK"):
            parts.append(tok.strip())
            continue
        # blockquote class="small" — аннотационная цитата
        for ch in re.split(r"(<blockquote[^>]*>.*?</blockquote>)", tok, flags=re.S):
            m = re.match(r"<blockquote([^>]*)>(.*?)</blockquote>", ch, flags=re.S)
            if m:
                inner = m.group(2)
                if "small" in (m.group(1) or "").lower():
                    parts.append(blockquote_class_small(inner))
                else:
                    parts.append(_inline_to_markdown(inner))
                continue
            # шапка <p class="small">…</p> — обычным параграфом; прочие <p>
            ch = _inline_to_markdown(ch)
            ch = re.sub(r"(?:\n\s*){3,}", "\n\n", ch)
            if ch.strip():
                parts.append(ch.strip())
    text_show = "\n\n".join(p for p in parts if p.strip())
    text_show = re.sub(r"(?:\n\s*){3,}", "\n\n", text_show)
    return copy_html, text_show


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="файл с HTML-фрагментом")
    ap.add_argument("--stdin", action="store_true", help="читать HTML из stdin")
    args = ap.parse_args()
    if args.stdin or args.file == "-" or not args.file:
        data = sys.stdin.read()
    else:
        with open(args.file, encoding="utf-8") as f:
            data = f.read()
    copy_html, text_show = convert(data)
    bar = "=" * 60
    print(bar)
    print("ВАРИАНТ 1 — ДЛЯ КОПИРОВАНИЯ (HTML):")
    print(bar)
    print(copy_html)
    print()
    print(bar)
    print("ВАРИАНТ 2 — ДЛЯ ПОКАЗА (текст с лёгкой разметкой):")
    print(bar)
    print(text_show)


if __name__ == "__main__":
    main()
