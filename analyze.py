# -*- coding: utf-8 -*-
"""
AI 답변 노출 점검: 수집한 AI 답변(answers.csv)을 읽어 브랜드 노출을 분석하고 HTML 리포트를 만든다.

  python3 analyze.py                       # sample 폴더로 실행
  python3 analyze.py --questions 내질문.csv --answers 내답변.csv --config 내설정.json --out report.html

보는 지표
  - 언급률: 답변에 우리 브랜드가 나온 비율 (엔진별, 질문 유형별)
  - 첫 언급 순서: 여러 브랜드가 나올 때 우리 브랜드가 몇 번째로 나왔는지
  - 경쟁사 언급률: 같은 질문에서 경쟁사가 나온 비율
  - 인용 출처: 답변이 근거로 단 링크 중 우리 도메인 비율, 자주 인용된 도메인
외부 라이브러리 없이 파이썬 기본 기능만 사용한다.
"""
import argparse, csv, html, json, os
from collections import Counter, defaultdict
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))


def load(args):
    cfg = json.load(open(args.config, encoding="utf-8"))
    qs = {r["id"]: r for r in csv.DictReader(open(args.questions, encoding="utf-8"))}
    ans = list(csv.DictReader(open(args.answers, encoding="utf-8")))
    return cfg, qs, ans


def first_pos(text, names):
    pos = [text.find(n) for n in names if text.find(n) >= 0]
    return min(pos) if pos else None


def analyze(cfg, qs, ans):
    brands = {cfg["brand"]: cfg["brand_aliases"], **cfg["competitors"]}
    rows = []
    for a in ans:
        t = a["answer"]
        found = {b: first_pos(t, names) for b, names in brands.items()}
        order = [b for b, p in sorted(((b, p) for b, p in found.items() if p is not None), key=lambda x: x[1])]
        cites = [c for c in (a.get("citations") or "").split("|") if c.strip()]
        rows.append({
            **a, "type": qs.get(a["id"], {}).get("type", "-"), "question": qs.get(a["id"], {}).get("question", a["id"]),
            "mentioned": found[cfg["brand"]] is not None,
            "rank": order.index(cfg["brand"]) + 1 if cfg["brand"] in order else None,
            "others": [b for b in order if b != cfg["brand"]],
            "cites": cites,
            "own_cite": any(urlparse(c).netloc in cfg["brand_domains"] for c in cites),
        })
    return rows


def rate(rs, key="mentioned"):
    return (sum(1 for r in rs if r[key]) / len(rs)) if rs else 0


def report(cfg, rows, out):
    brand = cfg["brand"]
    by_engine, by_type = defaultdict(list), defaultdict(list)
    for r in rows:
        by_engine[r["engine"]].append(r)
        by_type[r["type"]].append(r)
    comp = Counter(o for r in rows for o in r["others"])
    domains = Counter(urlparse(c).netloc for r in rows for c in r["cites"])
    all_cites = sum(domains.values())
    own = sum(n for d, n in domains.items() if d in cfg["brand_domains"])
    dates = sorted({r["date"] for r in rows})

    def bar(v):
        return f'<div class="bar"><span style="width:{v*100:.0f}%"></span></div><b>{v*100:.0f}%</b>'

    e = html.escape
    sec_engine = "".join(f"<tr><td>{e(k)}</td><td>{bar(rate(v))}</td><td>{sum(r['mentioned'] for r in v)}/{len(v)}</td></tr>" for k, v in by_engine.items())
    sec_type = "".join(f"<tr><td>{e(k)}</td><td>{bar(rate(v))}</td><td>{sum(r['mentioned'] for r in v)}/{len(v)}</td></tr>" for k, v in by_type.items())
    sec_comp = f"<tr><td>{e(brand)} (우리)</td><td>{bar(rate(rows))}</td><td>{sum(r['mentioned'] for r in rows)}회</td></tr>" + \
        "".join(f"<tr><td>{e(k)}</td><td>{bar(n/len(rows))}</td><td>{n}회</td></tr>" for k, n in comp.most_common())
    sec_dom = "".join(f"<tr><td>{e(d)}{' (우리)' if d in cfg['brand_domains'] else ''}</td><td>{n}회</td></tr>" for d, n in domains.most_common(8))
    detail = "".join(
        f"<tr><td>{e(r['engine'])}</td><td>{e(r['type'])}</td><td>{e(r['question'])}</td>"
        f"<td class='{'y' if r['mentioned'] else 'n'}'>{'노출' if r['mentioned'] else '미노출'}{'' if not r['rank'] else f' ({r['rank']}번째)'}</td>"
        f"<td>{e(', '.join(r['others']) or '-')}</td><td>{'있음' if r['own_cite'] else '-'}</td></tr>" for r in rows)
    gq = defaultdict(lambda: {"engines": [], "others": Counter()})
    for r in rows:
        if not r["mentioned"] and r["others"]:
            gq[r["question"]]["engines"].append(r["engine"])
            gq[r["question"]]["others"].update(r["others"])
    order = sorted(gq.items(), key=lambda x: -len(x[1]["engines"]))
    gaps = "".join(f"<li>{e(q)}<br><span class='s'>미노출 엔진 {len(v['engines'])}곳: {e(', '.join(v['engines']))} · 대신 언급: {e(', '.join(k for k, _ in v['others'].most_common()))}</span></li>" for q, v in order)

    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>AI 답변 노출 리포트 · {e(brand)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f6f6f4;color:#222;font-family:Pretendard,-apple-system,sans-serif;font-size:14px;line-height:1.6;word-break:keep-all}}
.w{{max-width:1100px;margin:0 auto;padding:28px}}h1{{font-weight:300;font-size:26px;margin:0}}h2{{font-weight:400;font-size:16px;margin:0 0 10px}}.sub{{color:#777;margin:4px 0 20px}}
.kpi{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}}.k{{background:#fff;border:1px solid #e3e3df;border-radius:10px;padding:14px}}.k div{{color:#777;font-size:12px}}.k b{{font-size:24px;font-weight:500}}
.g{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.c{{background:#fff;border:1px solid #e3e3df;border-radius:10px;padding:16px;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:7px 6px;border-top:1px solid #eee;text-align:left;vertical-align:top;font-size:13px}}th{{color:#888;font-weight:400}}
.bar{{display:inline-block;width:62%;height:8px;background:#eee;border-radius:4px;margin-right:8px;vertical-align:middle}}.bar span{{display:block;height:8px;background:#8aa6a0;border-radius:4px}}
.y{{color:#2f6b3c}}.n{{color:#9a4b4b}}ul{{margin:0;padding-left:18px}}li{{margin-bottom:8px}}.s{{color:#888;font-size:12px}}.note{{color:#888;font-size:12px}}</style></head><body><div class="w">
<h1>AI 답변 노출 리포트</h1><p class="sub">브랜드: {e(brand)} · 수집일: {e(', '.join(dates))} · 답변 {len(rows)}건</p>
<div class="kpi"><div class="k"><div>전체 언급률</div><b>{rate(rows)*100:.0f}%</b></div>
<div class="k"><div>상황형 질문 언급률</div><b>{rate(by_type.get('상황형', []))*100:.0f}%</b></div>
<div class="k"><div>첫 번째로 언급된 비율</div><b>{(sum(1 for r in rows if r['rank']==1)/len(rows))*100:.0f}%</b></div>
<div class="k"><div>인용 출처 중 우리 도메인</div><b>{(own/all_cites*100 if all_cites else 0):.0f}%</b></div></div>
<div class="g"><div class="c"><h2>엔진별 언급률</h2><table>{sec_engine}</table></div>
<div class="c"><h2>질문 유형별 언급률</h2><table>{sec_type}</table><p class="note">브랜드형: 질문에 브랜드명이 들어간 질문<br>상황형: 브랜드명 없이 상황만 묻는 질문</p></div>
<div class="c"><h2>경쟁사와 언급 비교</h2><table>{sec_comp}</table></div>
<div class="c"><h2>자주 인용된 출처</h2><table>{sec_dom}</table></div></div>
<div class="c"><h2>우선 개선할 질문</h2><p class="note">우리 브랜드는 빠지고 경쟁사만 언급된 질문입니다.<br>놓친 엔진이 많은 질문부터 콘텐츠를 보강합니다.</p><ul>{gaps or '<li>없음</li>'}</ul></div>
<div class="c"><h2>답변별 상세</h2><table><tr><th>엔진</th><th>유형</th><th>질문</th><th>우리 브랜드</th><th>함께 언급</th><th>우리 출처 인용</th></tr>{detail}</table></div>
<p class="note">AI 답변은 실행할 때마다 달라질 수 있습니다.<br>한 번의 수집 결과는 그 시점의 관측값으로 보고 같은 질문을 주기적으로 다시 수집해 추이로 판단합니다.</p>
</div></body></html>"""
    open(out, "w", encoding="utf-8").write(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--questions", default=os.path.join(HERE, "sample", "questions.csv"))
    ap.add_argument("--answers", default=os.path.join(HERE, "sample", "answers.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "report.html"))
    a = ap.parse_args()
    cfg, qs, ans = load(a)
    rows = analyze(cfg, qs, ans)
    report(cfg, rows, a.out)
    print(f"답변 {len(rows)}건 분석 · 전체 언급률 {rate(rows)*100:.0f}% · 리포트: {a.out}")


if __name__ == "__main__":
    main()
