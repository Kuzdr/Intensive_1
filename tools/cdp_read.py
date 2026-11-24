# -*- coding: utf-8 -*-
r"""Чтение страниц через обычный (не headless) Edge по протоколу отладки CDP.

Сайты с антибот-защитой (в первую очередь Timepad, поисковики, Telegram)
отдают `webfetch`/`requests` капчу или кольцо редиректов. Обычный браузер
с включённым JavaScript эти страницы открывает нормально. Скрипт открывает
URL в отдельном профиле Edge, ждёт загрузки и сохраняет готовый DOM в
`data/raw/cdp/<tag>.html` (папка в .gitignore).

    python -X utf8 tools\cdp_read.py tp4257910 https://fondnauk.timepad.ru/event/4257910/
    python -X utf8 tools\cdp_read.py yandex "https://yandex.ru/search/?text=..." yandex.ru
    python -X utf8 tools\cdp_read.py tgs "https://t.me/s/fondnauk?q=..." t.me --text

Третий позиционный аргумент — подстрока в адресе вкладки, по которой найти
нужную вкладку (полезно, если браузер открыл редирект). `--text` дополнительно
печатает видимый текст страницы.
"""
import argparse
import base64
import io
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "data", "raw", "cdp")
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PORT = 9224
PROFILE = os.path.join(OUTDIR, "edge_profile")


class WS(object):
    """Минимальный WebSocket-клиент для CDP (без внешних библиотек)."""

    def __init__(self, url):
        u = urlparse(url)
        self.sock = socket.create_connection((u.hostname, u.port or 80), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            "GET %s HTTP/1.1\r\nHost: %s:%s\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
            % (u.path, u.hostname, u.port or 80, key)
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        if b"101" not in buf.split(b"\r\n", 1)[0]:
            raise RuntimeError("handshake: " + buf[:200].decode("utf-8", "replace"))

    def send(self, text):
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        n = len(payload)
        head = bytearray([0x81])
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack("!H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack("!Q", n)
        head += mask
        self.sock.sendall(bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _recv_exact(self, n):
        out = b""
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise RuntimeError("socket closed")
            out += chunk
        return out

    def recv(self):
        b0, b1 = self._recv_exact(2)
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack("!H", self._recv_exact(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self._recv_exact(8))[0]
        if b1 & 0x80:
            mask = self._recv_exact(4)
            data = self._recv_exact(n)
            data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
        else:
            data = self._recv_exact(n)
        return data.decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def edge_path():
    for p in EDGE_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise RuntimeError("Не найден Microsoft Edge (установите Edge или поправьте EDGE_CANDIDATES)")


def wait_target(needle=None, seconds=60):
    for _ in range(seconds):
        try:
            raw = urllib.request.urlopen("http://127.0.0.1:%d/json" % PORT, timeout=2).read()
            for t in json.loads(raw.decode("utf-8")):
                if t.get("type") != "page":
                    continue
                if needle is None or needle in t.get("url", ""):
                    return t
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("CDP-вкладка не найдена")


def visible_text(html):
    import re
    import html as H
    s = re.sub(r"<script[\s\S]*?</script>", " ", html)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|li|h[1-6]|tr|section)>", "\n", s)
    s = H.unescape(re.sub(r"<[^>]+>", " ", s))
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in s.splitlines() if line.strip())


def read(url, tag, needle=None, text=False, wait=8):
    os.makedirs(OUTDIR, exist_ok=True)
    proc = subprocess.Popen([
        edge_path(),
        "--remote-debugging-port=%d" % PORT,
        "--user-data-dir=" + PROFILE,
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,EdgeWallet",
        "--new-window",
        url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = WS(wait_target(needle)["webSocketDebuggerUrl"])
        counter = [10]

        def evaluate(expr):
            counter[0] += 1
            mid = counter[0]
            ws.send(json.dumps({"id": mid, "method": "Runtime.evaluate",
                                "params": {"expression": expr, "returnByValue": True}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid:
                    return msg.get("result", {}).get("result", {}).get("value", "")

        for _ in range(wait):
            if evaluate("document.readyState") == "complete" and len(
                    evaluate("document.documentElement.outerHTML")) > 1000:
                break
            time.sleep(1)
        time.sleep(2)
        html = evaluate("document.documentElement.outerHTML")
        ws.close()
        path = os.path.join(OUTDIR, "%s.html" % tag)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print("%s: size=%d title=%s" % (
            tag, len(html), html.split("<title>")[-1].split("</title>")[0][:80]))
        low = html.lower()
        for marker in ("showcaptcha", "captcha", "робот"):
            print("  %-12s %d" % (marker, low.count(marker)))
        print("  файл:", os.path.relpath(path, ROOT))
        if text:
            print(visible_text(html))
        return path
    finally:
        proc.terminate()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tag", help="короткое имя для файла DOM")
    ap.add_argument("url", help="адрес страницы")
    ap.add_argument("needle", nargs="?", help="подстрока в адресе вкладки")
    ap.add_argument("--text", action="store_true", help="печатать видимый текст")
    ap.add_argument("--wait", type=int, default=8, help="секунд ожидания загрузки")
    a = ap.parse_args()
    read(a.url, a.tag, a.needle, a.text, a.wait)


if __name__ == "__main__":
    main()
