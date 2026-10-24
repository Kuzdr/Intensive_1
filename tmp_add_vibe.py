import json
events = json.load(open("data/events.json", encoding="utf-8"))
proto = json.load(open("data/prototypes/TP-4261104/prototype.json", encoding="utf-8"))
entry = {
  "id": 4261104,
  "proto_id": "TP-4261104",
  "lectory": proto.get("lectory","Лекторий.ВДНХ"),
  "date_iso": proto["date_iso"],
  "time_start": proto.get("time_start","15:00"),
  "time_end": proto.get("time_end","16:30"),
  "city": "Москва",
  "place": "ВДНХ, центр «Космонавтика и авиация»",
  "place_full": proto.get("place","Москва, ВДНХ, центр «Космонавтика и авиация»"),
  "lecturer": proto.get("lecturer","Дмитрий Вибе"),
  "title": proto.get("title","Солнце и другие звёзды"),
  "types": proto.get("types",["Лекция"]),
  "topics": proto.get("topics",["Космос","Астрофизика"]),
  "price_short": "Бесплатно",
  "age": "12+",
  "url": proto.get("url"),
  "sources": proto.get("sources",[]),
  "annot": proto.get("annot",""),
  "detail_html": proto.get("desc_html","") + "".join(proto.get("extra_html",[])),
  "detail_text": "",
  "authors": proto.get("authors",[])
}
events.append(entry)
json.dump(events, open("data/events.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("done")
