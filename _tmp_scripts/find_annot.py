# -*- coding: utf-8 -*-
import re, io
# возьмём блок detail_text события 8863 из сохранённого JSON (если есть)
for fn in [r"C:\Users\mv\AppData\Local\Temp\opencode\elt_surdin_page.json",
           r"C:\Users\mv\AppData\Local\Temp\opencode\surdin_detail.json",
           r"C:\Users\mv\AppData\Local\Temp\opencode\surdin_data.json"]:
    try:
        js = io.open(fn, encoding="utf-8").read()
    except Exception:
        continue
    m = re.search(r'"detail_text":\s*"(.*?)"', js, re.S)
    if m:
        txt = m.group(1).encode("utf-8").decode("unicode_escape")
        txt = re.sub(r"\\n", "\n", txt)
        io.open(r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_full_annot.txt","w",encoding="utf-8").write(txt)
        print("found in", fn)
        break
else:
    print("НЕТ detail_text-файла — возьму из visible")
