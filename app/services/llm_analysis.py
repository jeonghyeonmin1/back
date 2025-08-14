from openai import OpenAI
import re
import os
from dotenv import load_dotenv
import random
from datetime import datetime
from app import db
from app.models import Interview

load_dotenv()

def analysisByLLM(user_id, session_id=None, job="간호사"):
    print(f"[Analysis Start] analyzing user_id: {user_id}, session_id: {session_id}, job: {job}")

    client = OpenAI(
        # base_url="https://api.aimlapi.com/v1",
        # api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    if session_id:
        interviews = (Interview.query
                           .filter_by(user_id=user_id, session_id=session_id)
                           .order_by(Interview.question_order)
                           .all())
        print(f"[Analysis] Found {len(interviews)} interviews for session {session_id}")
    else:
        interviews = (Interview.query
                           .filter_by(user_id=user_id)
                           .order_by(Interview.timestamp)
                           .all())
        print(f"[Analysis] Found {len(interviews)} total interviews")
    
    if not interviews:
        return "분석할 인터뷰 데이터가 없습니다."

    prompt_parts = []
    for idx, itv in enumerate(interviews, start=1):
        prompt_parts.append(
            f"---\n"
            f"질문 {idx}: {itv.question}\n"
            f"사용자 답변: {itv.useranswer}\n"
            # f"사용자 답변: {itv.LLM_gen_answer}\n"
            f"LLM 이전 답변: {itv.LLM_gen_answer}\n"
        )
    combined = "\n".join(prompt_parts)

    job_prompts = {
        "nurse": "너는 간호사 면접 준비를 도와주는 AI야.",
        "developer": "너는 개발자 면접 준비를 도와주는 AI야.",
        "doctor": "너는 의사 면접 준비를 도와주는 AI야.", 
        "planner": "너는 기획자 면접 준비를 도와주는 AI야.",
        "etc": "너는 면접 준비를 도와주는 AI야."
    }
    
    job_prompt = job_prompts.get(job, job_prompts["etc"])

    system_prompt = (
        f"{job_prompt} "
        "아래는 사용자가 진행한 모든 면접 질문과 답변이야:\n\n"
        f"{combined}\n\n"
        "각 질문별로 다음 형식으로 분석 결과를 출력해줘:\n"
        "{analysis} : (질문별 분석 내용)\n"
        "{score} : (0~100 사이 점수)\n"
        "그리고 마지막에 전체 면접에 대한 {summary}를 작성해줘.\n"
        "**<think> 같은 내부 지시는 절대 출력하지 말고**, 전부 한국어로 작성해."
    )

    response = client.chat.completions.create(
        # model="Qwen/Qwen3-235B-A22B-fp8-tput",
        model="qwen-turbo",

        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": "전체 인터뷰 분석해주세요."}
        ],
        temperature=0.7,
        top_p=0.7,
        frequency_penalty=1,
        max_tokens=2048
    )
    
    message = response.choices[0].message.content
    if "</think>" in message:
        message = message.split("</think>", 1)[1]
    print("[LLM Response]", message)
    
    analysis_pattern = re.compile(r"(?:\{analysis\}|analysis)\s*:\s*(.+?)(?=(?:\{score\}|score)\s*:|$)", re.IGNORECASE | re.DOTALL)
    score_pattern    = re.compile(r"(?:\{score\}|score)\s*:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
    summary_pattern  = re.compile(r"(?:\{summary\}|summary)\s*:\s*(.+?)(?=\n\n|\Z)", re.IGNORECASE | re.DOTALL)

    analyses = analysis_pattern.findall(message)
    scores   = score_pattern.findall(message)
    summary_matches = summary_pattern.findall(message)
    summary = summary_matches[-1].strip() if summary_matches else ""
    
    print(f"[Parsing Results] Found {len(analyses)} analyses, {len(scores)} scores")
    print(f"[Analyses] {analyses}")
    print(f"[Scores] {scores}")
    print(f"[Summary] {summary}")

    min_length = min(len(interviews), len(analyses), len(scores))
    print(f"[DB Save] Processing {min_length} interviews")
    
    for i in range(min_length):
        itv = interviews[i]
        anal = analyses[i] if i < len(analyses) else "분석 결과 없음"
        sc = scores[i] if i < len(scores) else "0"
        
        itv.analysis = anal.strip()
        itv.summary = summary.strip()   
        try:
            itv.score = float(sc)
        except ValueError:
            itv.score = 0.0
            print(f"[Warning] Invalid score format for interview {i}: {sc}")
    
    for i in range(min_length, len(interviews)):
        interviews[i].analysis = "분석 결과 없음 (기본값)"
        interviews[i].score = 0.0

    if hasattr(interviews[0], 'summary'):
        interviews[0].summary = summary

    db.session.commit()
    return summary