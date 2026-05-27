# 计算EM、F1、BLEU-1等指标，评估模型的表现
import argparse
import json
import re
import string
from collections import Counter, defaultdict
from pathlib import Path

from nltk.stem import PorterStemmer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction


stemmer = PorterStemmer()
smooth = SmoothingFunction().method1


def normalize_answer(text: str) -> str:
    text = str(text).lower().strip()

    # Protect decimal points like 3.14
    text = re.sub(r"(\d)\.(\d)", r"\1DOT\2", text)

    # Keep underscore so IDs like IMG_001 are preserved
    punctuation = string.punctuation.replace("_", "")
    text = "".join(" " if ch in punctuation else ch for ch in text)

    # Restore decimal points
    text = text.replace("DOT", ".")

    # Remove common articles/conjunctions
    text = re.sub(r"\b(a|an|the|and)\b", " ", text)

    # Collapse whitespace
    text = " ".join(text.split())
    return text


def exact_match_score(prediction: str, ground_truth: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


def f1_score(prediction: str, ground_truth: str) -> float:
    pred_tokens = [stemmer.stem(x) for x in normalize_answer(prediction).split()]
    gt_tokens = [stemmer.stem(x) for x in normalize_answer(ground_truth).split()]

    if len(pred_tokens) == 0 and len(gt_tokens) == 0:
        return 1.0
    if len(pred_tokens) == 0 or len(gt_tokens) == 0:
        return 0.0

    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(gt_tokens)
    return 2 * precision * recall / (precision + recall)


def bleu_1_score(prediction: str, ground_truth: str) -> float:
    pred_tokens = normalize_answer(prediction).split()
    gt_tokens = normalize_answer(ground_truth).split()

    if len(pred_tokens) == 0 or len(gt_tokens) == 0:
        return 0.0

    return sentence_bleu(
        [gt_tokens],
        pred_tokens,
        weights=(1, 0, 0, 0),
        smoothing_function=smooth,
    )


def evaluate_results(result_path: Path):
    data = json.loads(result_path.read_text(encoding="utf-8"))

    by_cat = defaultdict(lambda: {"EM": [], "F1": [], "BLEU_1": []})
    overall = {"EM": [], "F1": [], "BLEU_1": []}

    for item in data:
        pred = str(item.get("system_answer", ""))
        gt = str(item.get("original_answer", ""))
        cat = str(item.get("category", "UNK"))

        em = exact_match_score(pred, gt)
        f1 = f1_score(pred, gt)
        bleu1 = bleu_1_score(pred, gt)

        by_cat[cat]["EM"].append(em)
        by_cat[cat]["F1"].append(f1)
        by_cat[cat]["BLEU_1"].append(bleu1)

        overall["EM"].append(em)
        overall["F1"].append(f1)
        overall["BLEU_1"].append(bleu1)


    print("\n=== Overall ===")
    for k, v in overall.items():
        avg = sum(v) / len(v) if v else 0.0
        print(f"{k}: {avg:.4f}")

    print("\n=== By Category ===")
    for cat in sorted(by_cat):
        print(f"[{cat}]")
        for k, v in by_cat[cat].items():
            avg = sum(v) / len(v) if v else 0.0
            print(f"  {k}: {avg:.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result_file",
        default="../result_debug/qwen2-5-vl-7b/FUMemory/AI_Robotics_Automation_Future_Tech_results.json",
        help="Path to results.json relative to benchmark/run/",
    )
    args = parser.parse_args()

    result_path = Path(args.result_file).resolve()
    if not result_path.exists():
        raise FileNotFoundError(f"Result file not found: {result_path}")

    evaluate_results(result_path)


if __name__ == "__main__":
    main()