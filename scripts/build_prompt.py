import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict

import openai


# ──────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────
PLACEHOLDER_PATTERN = re.compile(r"{(\w+)}")


def parse_vars(var_list):
    """--var key=value …  →  dict"""
    vars_dict: Dict[str, str] = {}
    for item in var_list or []:
        if "=" not in item:
            raise ValueError(f"--var 인자 형식 오류: '{item}' (key=value)")
        k, v = item.split("=", 1)
        vars_dict[k] = v
    return vars_dict


def fill_placeholders(template: str, vars_dict: Dict[str, str]):
    """template 문자열의 {placeholder} 를 vars_dict 값으로 치환"""
    missing = []
    def repl(match):
        key = match.group(1)
        if key not in vars_dict:
            missing.append(key)
            return match.group(0)
        return vars_dict[key]

    result = PLACEHOLDER_PATTERN.sub(repl, template)
    if missing:
        raise KeyError(f"치환 값 누락: {missing}. --var {missing[0]}=값 형태로 전달하세요.")
    return result


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def select_step_info(template: dict, step: int):
    for item in template["workflow"]:
        if item["step"] == step:
            return item
    raise ValueError(f"step={step} 을(를) 템플릿에서 찾을 수 없습니다.")


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Docs Generator prompt builder (o3)")
    parser.add_argument("--json", required=True,
                        help="workflow_template.json 경로")
    parser.add_argument("--step", type=int, required=True,
                        help="실행할 workflow step 번호")
    parser.add_argument("--var", action="append",
                        help="자리표시자 치환 값 (key=value). 여러 번 사용 가능.")
    parser.add_argument("--out", metavar="PATH",
                        help="응답을 저장할 파일 경로 (생략 시 STDOUT)")
    parser.add_argument("--max-tokens", type=int, default=1500,
                        help="o3 응답 최대 토큰 수 (기본 1500)")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="LLM temperature (기본 0.7)")
    args = parser.parse_args()

    # 1. 템플릿 로드
    template = read_json(Path(args.json))
    step_info = select_step_info(template, args.step)
    prompt_template = step_info["assistant_prompt"]

    # 2. 자리표시자 치환
    vars_dict = parse_vars(args.var)
    try:
        final_prompt = fill_placeholders(prompt_template, vars_dict)
    except KeyError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # 3. o3 모델 호출
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        print("❌ OPENAI_API_KEY 환경변수 설정 필요", file=sys.stderr)
        sys.exit(1)

    print(f"▶️  o3 요청 중… (step {args.step}, max_tokens={args.max_tokens})", file=sys.stderr)
    response = openai.chat.completions.create(
        model="o3",
        messages=[
            {"role": "system", "content": "You are an expert educational content generator."},
            {"role": "user", "content": final_prompt}
        ],
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    content = response.choices[0].message.content.strip()

    # 4. 저장/출력
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"✅ 결과 저장: {out_path}", file=sys.stderr)
    else:
        print(content)


if __name__ == "__main__":
    main()
