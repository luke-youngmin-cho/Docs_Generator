import argparse, json, sys

parser = argparse.ArgumentParser()
parser.add_argument("--json-file")
parser.add_argument("--json")
parser.add_argument("--step", type=int, required=True)
args = parser.parse_args()

# ① 파일 경로로 읽기 우선
if args.json_file:
    with open(args.json_file, encoding="utf-8") as f:
        template = json.load(f)
# ② env 로 들어온 one-liner JSON 사용
elif args.json:
    template = json.loads(args.json)
else:
    sys.exit("❌ JSON template does not exist")

step_info = next(w for w in template["workflow"] if w["step"] == args.step)
prompt = step_info["assistant_prompt"]
print(prompt)  # 필요에 따라 파일 저장·OpenAI 호출 등
