"""錨點鏈驗證器 —— **任何人都可以自己跑,不需要相信我們**
====================================================================
🔴🔴 為什麼有這支檔案(2026-09-05)

公開頁 `lab.html` 上印著一句宣稱:

    ✓ 帳本不可竄改(hash chain)

而在這支檔案出現之前,**這條鏈從來沒有被任何程式驗證過**。
`anchor.py` 只有 `append_chain()`(寫),沒有任何 `verify`(讀)。
也就是說我們**寫了一條鏈,然後宣稱它不可竄改,但沒有人檢查過它**。

⭐ 一條沒有人驗證的雜湊鏈是裝飾品,不是證據。
   而「沒實測過的不准說好了」是公司的最高標準之一。

所以這支檔案做兩件事:
1. 讓我們自己在每次發佈時驗一遍(`tests/test_anchor_chain_verifies.py` 會跑它)
2. **隨鏈一起發佈到公開 repo**,讓不相信我們的人可以自己下載、自己跑

🔴 這支檔案**刻意不 import 這個專案的任何東西**,只用 Python 標準庫。
   外面的人拿到 `anchor_chain.json` 跟這支檔案就能驗,不需要我們的程式碼。

--------------------------------------------------------------------
## 它能證明什麼、不能證明什麼(這段話比程式本身重要)

**能證明**:
- 鏈是連續的(seq 0..N-1 不缺不跳)
- 每一筆的 `prev` 確實等於前一筆的 `hash`
- 每一筆的 `hash` 確實是該筆其餘欄位的 SHA-256

→ 推論:**任何人事後想改動鏈中任何一筆,都必須把它後面每一筆全部重算。**

**不能證明**:
- 🔴 **不能證明我們沒有整條重算。** 如果我們願意把整條鏈重寫一遍,
  這支驗證器一樣會說「通過」。雜湊鏈只防「改一筆」,不防「重寫全部」。
  防重寫要靠**外部時間戳**(把 hash 推到我們控制不了的地方並留下時間紀錄)——
  本專案的做法是每日推送到公開 git repo,commit 時間由 GitHub 記錄。
  那份證據在 git 歷史裡,不在這支程式裡。
- 不能證明 `ledger_head` 對應的帳本內容是對的(那要另外拿帳本來算)
- 不能證明實驗本身有意義

用法:
    python verify_chain.py                      # 驗預設位置的鏈
    python verify_chain.py path/to/anchor_chain.json
退出碼 0 = 通過,1 = 有問題。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

#: 發佈到公開 repo 之後,鏈就躺在這支檔案旁邊。
DEFAULT_NAMES = ("anchor_chain.json", "data/shadow/anchor_chain.json")

#: 參與雜湊的欄位 = 除了 `hash` 以外的全部。
#: 🔴 這裡**不寫死欄位清單**。寫死的話,以後 anchor.py 多加一個欄位,
#:   驗證器會照舊算出「通過」,而那個新欄位根本沒有被保護 ——
#:   一道驗不到新東西的驗證器,比沒有驗證器更危險(它會給人安全感)。
HASH_EXCLUDE = ("hash",)


def entry_hash(entry: dict) -> str:
    """重算一筆的雜湊。必須與 `anchor.py:append_chain` 的算法逐字一致。"""
    body = {k: v for k, v in entry.items() if k not in HASH_EXCLUDE}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def check_published(chain: list, folder: str) -> dict:
    """比對「鏈上記的雜湊」與「資料夾裡那些檔案現在的雜湊」。

    🔴🔴 為什麼需要這一段(2026-09-05)

    在此之前,鏈只保護 PROTOCOL 與引擎程式碼 —— 而讀者在頁面上看到的
    每一個數字都來自 `dashboard_data.json`,它的雜湊**不在鏈裡**。
    頁面卻把「帳本不可竄改(hash chain)」寫在那些數字**旁邊**。
    改掉那個檔案裡任何一個數字,整條鏈照樣通過。

    ⭐ 「有密碼學保護」與「讀者以為有密碼學保護」之間的落差,
      本身就是一種不實陳述 —— 即使我們沒有動過任何數字。

    🔴 三種結果必須分開,不可混同:通過 / 不符 / **沒有檔案可比對**。
      把第三種算成「通過」,等於「查不到」被當成「沒問題」。
    """
    latest = chain[-1] if chain else {}
    recorded = latest.get("published") or {}
    if not recorded:
        return {"state": "未記錄", "rows": [], "mismatch": 0, "missing": 0,
                "detail": "鏈的最後一筆沒有 published 欄位 —— "
                          "這一筆是在把公開檔案納入保護之前寫的"}
    rows, mismatch, missing = [], 0, 0
    for fn, want in sorted(recorded.items()):
        fp = os.path.join(folder, fn)
        if want == "MISSING":
            rows.append((fn, "錨定當時就不存在", "—"))
            missing += 1
            continue
        if not os.path.exists(fp):
            rows.append((fn, want, "本機沒有這個檔案"))
            missing += 1
            continue
        raw = open(fp, "rb").read()
        got = hashlib.sha256(raw).hexdigest()[:16]
        if got != want:
            # 🔴 分辨「換行差異」與「內容被改」——這兩件事完全不同,
            #   而只喊一句「不符」會讓人以為是後者。
            #   實測踩過(seq 48):錨定時在 Windows 上對 CRLF 版取雜湊,
            #   而 git 送出的是 LF 版 → 三個檔案被判「竄改」,
            #   但它們一個位元組都沒被人動過。
            #   ⭐ 一個會誣指自己的驗證器比沒有驗證器更糟:它訓練所有人忽略紅燈。
            #   🔴 但這**不是免死金牌**:仍然判為不符,只是多說一句診斷。
            CRLF = (chr(13) + chr(10)).encode()
            LF = chr(10).encode()
            for variant, label in ((raw.replace(LF, CRLF), "CRLF"),
                                   (raw.replace(CRLF, LF), "LF")):
                if hashlib.sha256(variant).hexdigest()[:16] == want:
                    got = got + "(內容相同,只差換行:鏈上記的是 %s 版)" % label
                    break
        rows.append((fn, want, got))   # got 可能已附上換行差異的診斷
        if got != want:
            mismatch += 1
    state = "不符" if mismatch else ("部分未比對" if missing else "通過")
    return {"state": state, "rows": rows, "mismatch": mismatch,
            "missing": missing, "detail": ""}


def verify(chain: list) -> dict:
    """回傳一份**逐項**結果。不要只回一個 True/False ——
    只回布林值的話,壞掉時沒有人知道壞在哪一筆、哪一種。"""
    problems = []

    if not isinstance(chain, list):
        return {"ok": False, "n": 0,
                "problems": [{"kind": "格式", "detail": "鏈不是一個陣列"}],
                "duplicates": {}, "checked": 0}

    if not chain:
        # 🔴 空鏈**不算通過**。「查不到」不等於「沒問題」——
        #    一個空檔案讓驗證器印出綠燈,正是最糟的失敗模式。
        return {"ok": False, "n": 0,
                "problems": [{"kind": "空鏈",
                              "detail": "鏈裡一筆都沒有 —— 這不是「通過」,是「沒有東西可驗」"}],
                "duplicates": {}, "checked": 0}

    for i, e in enumerate(chain):
        missing = [k for k in ("seq", "prev", "hash") if k not in e]
        if missing:
            problems.append({"kind": "缺欄位", "seq": e.get("seq", f"索引{i}"),
                             "detail": f"缺 {missing}"})
            continue

        if e["seq"] != i:
            problems.append({"kind": "seq 不連續", "seq": e["seq"],
                             "detail": f"陣列索引 {i} 的 seq 是 {e['seq']}"})

        expect_prev = chain[i - 1]["hash"] if i else "0" * 64
        if e["prev"] != expect_prev:
            problems.append({"kind": "prev 斷鏈", "seq": e["seq"],
                             "detail": f"prev={e['prev'][:16]}… "
                                       f"但前一筆的 hash 是 {expect_prev[:16]}…"})

        got = entry_hash(e)
        if got != e["hash"]:
            problems.append({"kind": "hash 對不上", "seq": e["seq"],
                             "detail": f"檔案裡寫 {e['hash'][:16]}… "
                                       f"重算是 {got[:16]}… → 這一筆的內容被改過"})

    # 同一個決策日出現多筆 —— **不是錯誤**,但一定要講出來。
    # 🔴 它可能是無害的(重跑發佈),也可能是有人重跑到滿意為止。
    #    差別在於 `ledger_head` 有沒有跟著變:帳本一樣 = 沒有重述資料。
    by_day = {}
    for e in chain:
        by_day.setdefault(e.get("days_recorded"), []).append(e)
    duplicates = {}
    for day, es in by_day.items():
        if len(es) > 1:
            heads = sorted({x.get("ledger_head") for x in es})
            trees = sorted({x.get("tree_root") for x in es})
            duplicates[day] = {
                "筆數": len(es),
                "seq": [x.get("seq") for x in es],
                "utc": [x.get("utc") for x in es],
                "帳本幾種": len(heads),
                "程式碼幾種": len(trees),
                "帳本是否被重述": len(heads) > 1,
            }

    return {"ok": not problems, "n": len(chain), "checked": len(chain),
            "problems": problems, "duplicates": duplicates}


def _find_default() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.path.join(here, "..", "data", "shadow"),
                 os.path.join(here, "..", "..", "..", "landing-page",
                              "data", "shadow")):
        for name in DEFAULT_NAMES:
            p = os.path.normpath(os.path.join(base, name))
            if os.path.exists(p):
                return p
    return ""


def main(argv: list) -> int:
    path = argv[1] if len(argv) > 1 else _find_default()
    if not path or not os.path.exists(path):
        # 🔴 找不到檔案是**失敗**,不是「沒事」。
        print("✗ 找不到 anchor_chain.json。")
        print("  用法:python verify_chain.py <anchor_chain.json 的路徑>")
        return 1

    with open(path, encoding="utf-8") as fh:
        chain = json.load(fh)

    r = verify(chain)
    print(f"錨點鏈:{path}")
    print(f"  筆數:{r['n']}(全部驗過 {r['checked']} 筆)")

    if r["problems"]:
        print(f"\n✗ 發現 {len(r['problems'])} 個問題:")
        for p in r["problems"]:
            print(f"   [{p['kind']}] seq={p.get('seq')} — {p['detail']}")
    else:
        print("  ✓ seq 連續、prev 全部對得上、每一筆 hash 重算相符")

    if r["duplicates"]:
        print("\n⚠️ 同一個決策日有多筆錨點(不是錯誤,但要說清楚):")
        for day, d in sorted(r["duplicates"].items(), key=lambda kv: (kv[0] is None, kv[0])):
            print(f"   第 {day} 決策日:{d['筆數']} 筆(seq {d['seq']})")
            for t in d["utc"]:
                print(f"      {t}")
            if d["帳本是否被重述"]:
                print(f"      🔴 這幾筆的 ledger_head **不一樣**"
                      f"({d['帳本幾種']} 種)—— 帳本被重述過,必須解釋")
            else:
                print(f"      ✓ ledger_head 完全相同 —— 帳本沒有被重述,"
                      f"只是同一天發佈了多次")
                if d["程式碼幾種"] > 1:
                    print(f"      ℹ️ tree_root 有 {d['程式碼幾種']} 種 —— "
                          f"程式碼在這幾次之間改過(這正是錨點要記錄的事)")

    pub = check_published(chain, os.path.dirname(os.path.abspath(path)))
    latest = chain[-1] if chain else {}
    print("")
    print("讀者看到的那些檔案(頁面上的數字就住在裡面):")
    if pub["state"] == "未記錄":
        print("   ⚠️ " + pub["detail"])
    else:
        for fn, want, got in pub["rows"]:
            mark = "✓" if want == got else ("⚠️" if "—" in str(got) or "沒有" in str(got) else "✗")
            print("   %s %-22s 鏈上 %s  現在 %s" % (mark, fn, want, got))
        if pub["state"] == "通過":
            print("   ✓ 全部相符 —— 你讀到的數字就是被錨定的那一份")
        elif pub["state"] == "不符":
            # 🔴🔴 這裡必須把**這支程式分辨不出來的事**講出來。
            #
            #   錨點是每天 00:36 UTC 拍一次快照。任何在那之後的**正常更新**
            #   (例如我們當天補了一則 CHANGELOG)都會讓檔案跟錨點不同。
            #   而「正常更新」與「被竄改」在這支程式眼裡**長得一模一樣**。
            #
            #   ⭐ 如果只印「✗ 不符」,它會在我們每次正常更新時喊狼來了,
            #     然後所有人就開始忽略紅燈 —— 那比沒有驗證器更糟。
            #     所以印出不符,同時明說它分辨不出哪一種、以及去哪裡分辨。
            print("   ✗ 有 %d 個檔案跟最後一筆錨點記的不一樣" % pub["mismatch"])
            print("     最後一筆錨點:seq %s(%s)" %
                  (latest.get("seq"), latest.get("utc")))
            print("     這可能是兩種完全不同的事,而**這支程式分辨不出來**:")
             
            print("       (a) 該時點之後檔案被正常更新過(下一次錨定就會涵蓋)")
            print("       (b) 內容被竄改")
            print("     要分辨:看公開 repo 的 git 歷史 —— 每一次改動都有",
                  "commit 時間與內容,由 GitHub 記錄,不是我們說了算。")
        else:
            print("   ⚠️ 有 %d 個檔案沒有比對到(這不是通過,是沒驗)" % pub["missing"])

    print("\n🔴 這支驗證器**不能**證明我們沒有整條重算。")
    print("   雜湊鏈只防「改一筆」。防「重寫全部」要靠外部時間戳 ——")
    print("   本專案是每日推送到公開 git repo,commit 時間由 GitHub 記錄,")
    print("   那份證據在 git 歷史裡,不在這支程式裡。")

    # 🔴 公開檔案對不上也算失敗 —— 鏈自己自洽但數字被換掉,
    #   對讀者來說是更嚴重的一種壞掉。
    return 0 if (r["ok"] and pub["state"] != "不符") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
