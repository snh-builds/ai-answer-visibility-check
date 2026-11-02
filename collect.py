# -*- coding: utf-8 -*-
"""
(선택) OpenAI API로 질문 목록의 답변을 자동 수집해 answers.csv에 추가한다.
ChatGPT·Gemini·Perplexity 화면에서 직접 복사한 답변을 answers.csv에 붙여 넣어도 분석은 똑같이 된다.

  export OPENAI_API_KEY=...    # 키는 코드나 파일에 적지 않고 환경 변수로만 넣는다
  python3 collect.py --questions sample/questions.csv --answers my_answers.csv
"""
import argparse, csv, datetime, json, os, urllib.request

def ask(question, model):
    body = {"model": model, "input": question, "tools": [{"type": "web_search"}]}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                                          "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=120))
    text, cites = [], []
    for item in data.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") == "output_text":
                text.append(c.get("text", ""))
                cites += [a["url"] for a in c.get("annotations", []) if a.get("type") == "url_citation"]
    return " ".join(text).strip(), "|".join(dict.fromkeys(cites))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--model", default="gpt-4.1-mini")
    a = ap.parse_args()
    new = not os.path.exists(a.answers)
    with open(a.answers, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "engine", "id", "answer", "citations"])
        for q in csv.DictReader(open(a.questions, encoding="utf-8")):
            text, cites = ask(q["question"], a.model)
            w.writerow([datetime.date.today().isoformat(), "OpenAI API", q["id"], text, cites])
            print("수집:", q["id"])

if __name__ == "__main__":
    main()
