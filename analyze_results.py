import json
import pathlib
from difflib import SequenceMatcher

THRESHOLD = 0.75
outputs = pathlib.Path("outputs")

for result_path in sorted(outputs.rglob("result.json")):
    label = result_path.parts[-3]
    v = json.loads(result_path.read_text(encoding="utf-8"))
    winner = v["winner"]
    expl = v["explanation"][:250]

    # Load conversation
    conv_path = result_path.parent / "conversation.jsonl"
    turns = []
    if conv_path.exists():
        turns = [json.loads(line) for line in conv_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Novelty check
    by_agent = {}
    for t in turns:
        by_agent.setdefault(t["agent"], []).append(t)
    repeats = []
    for agent, aturns in by_agent.items():
        for i in range(1, len(aturns)):
            r = SequenceMatcher(None, aturns[i-1]["argument"].lower(), aturns[i]["argument"].lower()).ratio()
            if r > THRESHOLD:
                repeats.append((agent, aturns[i-1]["turn"], aturns[i]["turn"], round(r, 2)))

    skipped = [n for n in range(1, 21) if n not in [t["turn"] for t in turns]]

    print(f"=== {label} ===")
    print(f"  Turns: {len(turns)}/20  |  Skipped: {skipped if skipped else 'none'}")
    print(f"  Winner: {winner}")
    for agent, s in v["scores"].items():
        print(f"    {agent}: logic={s['logic']} evidence={s['evidence']} clarity={s['clarity']} persuasiveness={s['persuasiveness']} total={s['total']}")
    print(f"  Repeats (post-novelty): {repeats if repeats else 'none'}")
    print(f"  Verdict: {expl}")
    print()
