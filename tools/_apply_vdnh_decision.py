# -*- coding: utf-8 -*-
"""Однократное применение решения пользователя 26.11.2026 по ВДНХ."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATE_NOTE = "решение пользователя 26.11.2026"

UNDECIDED = {"4248": "4306394", "4249": "4306436"}
CHOSEN = {
    "4184": ("4288577", "TP-4288577"),
    "4266": ("4314826", "TP-4314826"),
}
REJECTED_SITE_IDS = [
    "4308", "4287", "4305", "4197", "427512", "4302", "4198", "4258",
    "4195", "4265", "4280", "4013", "4246",
]


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


# Исходные записи нужны для списка «не нужно».
pending_path = ROOT / "data/monitor/pending.json"
pending = json.loads(pending_path.read_text(encoding="utf-8"))
old_items = {x["external_id"]: x for x in pending["items"]}

# 1. pending.json — убрать решённые, остальные пометить.
kept = []
for item in pending["items"]:
    sid = item["external_id"]
    if sid in CHOSEN:
        continue
    if sid in UNDECIDED:
        item["status"] = "Не решено"
        item["note"] = "%s: оставить не решённым, вернуться позже" % DATE_NOTE
    elif sid in REJECTED_SITE_IDS:
        item["status"] = "Не нужно"
        item["note"] = "%s: отвергнуто" % DATE_NOTE
    kept.append(item)
pending["items"] = kept
pending["_comment"] = (
    "События с незавершённым решением. " + DATE_NOTE +
    ": две выбранные лекции ушли в прототипы, 13 отвергнуты, "
    "Фрейд и Юнг помечены «Не решено».")
dump(pending_path, pending)

# 2. known_by_source.json — статусы по site и добавление двух Timepad-ID.
kbs_path = ROOT / "data/monitor/known_by_source.json"
kbs = json.loads(kbs_path.read_text(encoding="utf-8"))
for item in kbs["sources"]["vdnh_site"]:
    sid = item["external_id"]
    if sid in CHOSEN:
        tp_id, proto = CHOSEN[sid]
        item["status"] = "В прототипе"
        item["note"] = "%s: прототип %s, Timepad %s%s" % (
            DATE_NOTE, proto, tp_id,
            "; переделать после открытия регистрации 04.12.2026"
            if sid == "4266" else "")
    elif sid in UNDECIDED:
        item["status"] = "Не решено"
        item["note"] = "%s: оставить не решённым" % DATE_NOTE
    elif sid in REJECTED_SITE_IDS:
        item["status"] = "Не нужно"
        item["note"] = "%s: отвергнуто" % DATE_NOTE

sources = kbs["sources"]
for source_key, tp_id, host, site_id in (
        ("vdnh_cosmos_timepad", "4288577", "cosmos-vdnh", "4184"),
        ("vdnh_lektorij_timepad", "4314826", "lektorij-vdnh", "4266")):
    if any(x["external_id"] == tp_id for x in sources[source_key]):
        continue
    sources[source_key].append({
        "external_id": tp_id,
        "url": "https://%s.timepad.ru/event/%s/" % (host, tp_id),
        "first_seen": "2026-11-26",
        "last_seen": "2026-11-26",
        "title_hint": "Прототип %s (ссылка найдена на странице vdnh.ru/events/%s/)" % (
            CHOSEN[site_id][1], site_id),
        "status": "В прототипе",
        "note": "Ссылки не было в ленте Timepad, найдена на странице ВДНХ.",
    })
dump(kbs_path, kbs)

# 3. Список «не нужно» — дополнить отвергнутыми.
nn_path = ROOT / "data/monitor/vdnh_not_needed_2026-11-26.json"
not_needed = json.loads(nn_path.read_text(encoding="utf-8"))
existing = {(x["source"], x["external_id"]) for x in not_needed}
for sid in REJECTED_SITE_IDS:
    if ("vdnh_site", sid) in existing:
        continue
    old = old_items[sid]
    not_needed.append({
        "source": "vdnh_site",
        "external_id": sid,
        "url": old["links"][0],
        "title": old["title"],
        "date": old["date"],
        "time": old["time"],
        "why": "%s: отвергнуто пользователем" % DATE_NOTE,
        "links": old["links"],
    })
dump(nn_path, not_needed)
print("pending:", len(pending["items"]), "not_needed:", len(not_needed))
