# -*- coding: utf-8 -*-
"""
GitHub Actions에서 실행 — 오늘(KST) 경주의 단승 배당을 코리아레이스 배당판에서 긁어 odds.js 생성.
앱은 odds.js를 불러와 다음 경기 예측에 배당을 반영한다. 발매 전이라 배당이 없으면 그냥 빈 채로 둔다.
PC 없이 GitHub이 자동 실행하므로 사용자는 폰에서 '최신 불러오기'만 누르면 된다.
"""
import re, html, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

HERE = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
BOARD_URL = "https://www.korearace.com/LiveData/RaceResult/raceBoard.asp?raceKey="
MEET_DIGIT = {"서울": "1", "부산경남": "3", "제주": "9"}
CIRCLED = {chr(0x2460 + i): i + 1 for i in range(20)}   # ①②③… → 1,2,3…
DELAY = 0.2


def fetch(key):
    time.sleep(DELAY)
    with urlopen(Request(BOARD_URL + key, headers=UA), timeout=25) as r:
        return r.read().decode("euc-kr", errors="replace")


def _rows(raw):
    src = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    src = re.sub(r"(?i)</tr>", "\n@@ROW@@", src)
    src = re.sub(r"(?i)<t[dh][^>]*>", "|", src)
    text = html.unescape(re.sub(r"<[^>]+>", " ", src))
    rows = []
    for chunk in text.split("@@ROW@@"):
        cells = [" ".join(c.split()) for c in chunk.split("|")]
        cells = [c for c in cells if c]
        if cells:
            rows.append(cells)
    return rows


def board_odds(key):
    """raceKey → {마번: 단승배당}. 배당판 행: [①마명, 인기도%, 단승, 연승, …] — 인기도% 있는 행만."""
    od = {}
    for c in _rows(fetch(key)):
        if len(c) < 3 or c[0][0] not in CIRCLED:
            continue
        if not re.fullmatch(r"\d+%", c[1]):
            continue
        if re.fullmatch(r"\d{1,3}(?:\.\d)?", c[2]):
            od[CIRCLED[c[0][0]]] = float(c[2])
    return od


def load_upcoming():
    txt = (HERE / "upcoming.js").read_text(encoding="utf-8")
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    return json.loads(m.group(1))


def main():
    today = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y%m%d")  # KST
    up = load_upcoming()
    out = {}
    fetched = 0
    for d in up.get("dates", []):
        if d != today:            # 오늘 경주만 (배당은 경주 당일에만 존재)
            continue
        for meet, lst in up["byDate"][d].items():
            dig = MEET_DIGIT.get(meet)
            if not dig:
                continue
            for r in lst:
                key = f"{d}{dig}{int(r['no']):02d}"
                fetched += 1
                try:
                    od = board_odds(key)
                except Exception as e:
                    print(f"  {key}: 조회 실패 {e}")
                    continue
                if od:
                    out[key] = {str(k): v for k, v in od.items()}
                    print(f"{key}: {meet} {r['no']}R · 배당 {len(od)}두")
    (HERE / "odds.js").write_text(
        "window.ODDS = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print(f"odds.js: 오늘({today}) {fetched}경주 조회 · 배당 있는 경주 {len(out)}")


if __name__ == "__main__":
    main()
