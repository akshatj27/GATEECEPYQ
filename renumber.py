import os
import json

def renumber_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        for idx, q in enumerate(data, start=1):
            if isinstance(q, dict):
                q['number'] = f"Question {idx}"
    elif isinstance(data, dict):
        for key, lst in data.items():
            if isinstance(lst, list):
                for idx, q in enumerate(lst, start=1):
                    if isinstance(q, dict):
                        q['number'] = f"Question {idx}"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    root_dir = "gate_questions"  # adjust if your output dir is different
    for dirpath, _, files in os.walk(root_dir):
        for fname in files:
            if fname.endswith('.json'):
                full = os.path.join(dirpath, fname)
                renumber_file(full)
                print(f"Renumbered {full}")
