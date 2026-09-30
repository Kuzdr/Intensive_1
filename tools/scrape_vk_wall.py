# -*- coding: utf-8 -*-
"""Читатель поста ВКонтакте через nojs-версию (nojs.vk.com).

Берёт текст поста со стены сообщества/пользователя и все внешние ссылки
в нём. Используется как дополнительный (подтверждающий) источник для
событий, например филиалов Политехнического музея.

nojs.vk.com отдаёт обычный HTML в UTF-8, текст поста лежит в элементе
`data-testid="post_text"`. Эмодзи в разметке — <img class="emoji" alt="…">,
переносы строк — <br>. Скрипт переводит это в читаемый текст.

Использование:

    python -X utf8 tools\\scrape_vk_wall.py https://vk.com/wall-231235627_250
    python -X utf8 tools\\scrape_vk_wall.py -231235627_250          -- короткая форма
    python -X utf8 tools\\scrape_vk_wall.py <url> --file page.html  -- не качать

Код возврата: 0 — пост извлечён, 1 — ошибка.
"""
import argparse
import html as html_mod
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
NOJS = "https://nojs.vk.com"

POST_RE = re.compile(r'data-testid="post_text"[^>]*>(.*?)</span>', re.S)
EMOJI_RE = re.compile(r'<img[^>]*alt="([^"]*)"[^>]*>')
BR_RE = re.compile(r"<br\s*/?>")
LINK_RE = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
AWAY_RE = re.compile(r"/away\.php\?")


def link_target(href: str) -> str:
    """Настоящий адрес ссылки: VK прячет внешние ссылки в /away.php?to=…"""
    if "/away.php" in href and "to=" in href:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
        if q.get("to"):
            return q["to"][0]
    return href


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def to_nojs(url: str) -> str:
    """`vk.com/wall-231235627_250` → `nojs.vk.com/wall-231235627_250`. """
    if url.startswith(NOJS):
        return url
    if url.startswith("/"):
        return NOJS + url
    if url.startswith("-"):
        return NOJS + "/wall" + url
    if "vk.com/" not in url:
        raise ValueError("не похоже на ссылку на пост VK: %s" % url)
    path = urllib.parse.urlparse(url).path.lstrip("/")
    return NOJS + "/" + path


def extract(html: str):
    """Возвращает (text, links) из поста или бросает ValueError."""
    m = POST_RE.search(html)
    if not m:
        raise ValueError("на странице не найден текст поста (data-testid=\"post_text\")")
    chunk = m.group(1)
    links = [link_target(href) for href, _ in LINK_RE.findall(chunk)]
    links = [l for l in links if l.startswith("http")]
    chunk = LINK_RE.sub(lambda x: html_mod.unescape(x.group(2)), chunk)
    chunk = EMOJI_RE.sub(lambda x: x.group(1), chunk)
    chunk = BR_RE.sub("\n", chunk)
    text = TAG_RE.sub("", chunk)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, sorted(set(links))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", help="ссылка на пост (vk.com/wall-<id>_<post> или -<id>_<post>)")
    ap.add_argument("--file", metavar="HTML", help="разбирать локально сохранённый HTML, не качать")
    args = ap.parse_args(argv)

    try:
        url = to_nojs(args.url)
        html = open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(url)
        text, links = extract(html)
    except Exception as exc:  # сеть, парсинг, нет поста
        sys.stderr.write("Ошибка: %s\n" % exc)
        return 1

    sys.stdout.write("ТЕКСТ ПОСТА:\n%s\n" % text)
    sys.stdout.write("\nВНЕШНИЕ ССЫЛКИ:\n")
    for l in links:
        sys.stdout.write(l + "\n")
    if not links:
        sys.stdout.write("(нет)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())