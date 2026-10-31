import json
from fetchers.sources import FlipkartFetcher

f = FlipkartFetcher()
html = f.get(f.BASE + "/offers-store").text
s = f._state(html)
print("state parsed:", s is not None)
if s:
    print("top-level keys:", list(s.keys())[:20])
    txt = json.dumps(s)
    print("size:", len(txt))
    for k in ("finalPrice", "pricing", "titles", "baseUrl", "productInfo", "totalDiscount"):
        print(k, txt.count(f'"{k}"'))
    open("state.json", "w", encoding="utf-8").write(txt)