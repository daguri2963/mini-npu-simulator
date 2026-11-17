"""Mini NPU: pure-Python multiply-accumulate pattern classifier."""

import argparse
import json
import math
import re
import time
from pathlib import Path


EPSILON = 1e-9
REPEATS = 10  # 과제의 최소 기준: 각 크기와 구현마다 MAC을 10회 호출한다.
CASE_KEY = re.compile(r"size_(\d+)_(\d+)\Z")
FILTER_KEY = re.compile(r"size_(\d+)\Z")


def make_pattern(size, label):
    """Generate an odd-sized binary Cross or X matrix."""
    if size < 3 or size % 2 == 0 or label not in ("Cross", "X"):
        raise ValueError("패턴 크기는 3 이상의 홀수이고 라벨은 Cross/X여야 합니다.")
    middle = size // 2
    return [
        [int((r == middle or c == middle) if label == "Cross"
             else (r == c or r + c == size - 1)) for c in range(size)]
        for r in range(size)
    ]


def validate_matrix(value, size, name):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("{}: {}개 행이 필요합니다.".format(name, size))
    for row_number, row in enumerate(value, 1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("{}: {}행에 {}개 열이 필요합니다.".format(name, row_number, size))
        for item in row:
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                raise ValueError("{}: 유한한 숫자만 허용합니다.".format(name))
    return value


def mac_2d(pattern, filter_matrix):
    """같은 위치의 값을 곱해 누적한다. 0×0은 가산점이 아니다."""
    score = 0.0
    for r in range(len(pattern)):
        for c in range(len(pattern[r])):
            score += pattern[r][c] * filter_matrix[r][c]
    return score


def flatten(matrix):
    return [item for row in matrix for item in row]


def mac_1d(pattern, filter_matrix):
    score = 0.0
    for i in range(len(pattern)):
        score += pattern[i] * filter_matrix[i]
    return score


def decide(score_a, score_b, label_a="A", label_b="B"):
    """모드와 무관하게 점수 차이가 epsilon 미만이면 동점이다."""
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def normalize_label(value):
    if not isinstance(value, str):
        raise ValueError("라벨은 문자열이어야 합니다.")
    labels = {"+": "Cross", "cross": "Cross", "x": "X"}
    result = labels.get(value.strip().lower())
    if result is None:
        raise ValueError("알 수 없는 라벨: {!r}".format(value))
    return result


def read_matrix(name, size=3):
    print("{} ({}줄, 줄마다 {}개 숫자; 첫 줄에 @Cross 또는 @X 입력 시 자동 생성):".format(
        name, size, size))
    rows = []
    while len(rows) < size:
        try:
            parts = input("  {}행> ".format(len(rows) + 1)).split()
        except EOFError:
            raise SystemExit("입력이 중단되었습니다.")
        if not rows and len(parts) == 1 and parts[0].lower() in ("@cross", "@x"):
            label = normalize_label(parts[0][1:])
            print("{} {}×{} 패턴 자동 생성 완료".format(label, size, size))
            return make_pattern(size, label)
        if len(parts) != size:
            print("입력 형식 오류: 각 줄에 {}개의 숫자를 공백으로 구분해 입력하세요.".format(size))
            continue
        try:
            row = [float(part) for part in parts]
            if not all(math.isfinite(x) for x in row):
                raise ValueError
        except ValueError:
            print("입력 형식 오류: 유한한 숫자만 입력하세요.")
            continue
        rows.append(row)
    return rows


def benchmark(matrix, filter_matrix, repeats=REPEATS):
    """동일 입력으로 각 MAC 함수 호출만 repeats회 재고 평균 ms를 반환한다.

    파일 읽기, 입력, 출력과 1D 변환은 타이머 밖에서 처리한다. 아주 짧은
    호출에는 타이머/반복문 비용과 시스템 부하가 섞이므로 수치는 참고값이다.
    """
    if repeats < 10:
        raise ValueError("성능 측정은 최소 10회 반복해야 합니다.")
    flat_matrix = flatten(matrix)
    flat_filter = flatten(filter_matrix)
    timings = []
    for function, left, right in (
        (mac_2d, matrix, filter_matrix),
        (mac_1d, flat_matrix, flat_filter),
    ):
        start = time.perf_counter_ns()
        for _ in range(repeats):
            function(left, right)
        timings.append((time.perf_counter_ns() - start) / repeats / 1_000_000)
    return timings


def print_performance(sizes, filters=None, custom_three=None):
    print("\n[성능 분석] MAC 함수 호출 평균 / {}회".format(REPEATS))
    print("{:>8} {:>14} {:>14} {:>12}".format("크기", "2D (ms)", "1D (ms)", "연산 횟수"))
    for size in sizes:
        if size == 3 and custom_three is not None:
            pattern, filter_matrix = custom_three
        else:
            pattern = make_pattern(size, "Cross")
            filter_matrix = filters.get(size, {}).get("Cross") if filters else None
            if filter_matrix is None:
                filter_matrix = make_pattern(size, "Cross")
        two_d, one_d = benchmark(pattern, filter_matrix)
        print("{:>3}×{:<4} {:>14.6f} {:>14.6f} {:>12}".format(size, size, two_d, one_d, size * size))
    print("※ 변환과 입출력 시간 제외. 1D 변환 비용은 별도입니다.")


def user_mode():
    print("\n[필터 입력]")
    filter_a = read_matrix("필터 A")
    filter_b = read_matrix("필터 B")
    print("필터 A/B 저장 완료 (각 3×3)")
    print("\n[패턴 입력]")
    pattern = read_matrix("패턴")
    score_a = mac_2d(pattern, filter_a)
    score_b = mac_2d(pattern, filter_b)
    result = decide(score_a, score_b)
    print("\n[MAC 결과]")
    print("A 점수: {!r}".format(score_a))
    print("B 점수: {!r}".format(score_b))
    print("판정: {}".format("판정 불가 (UNDECIDED)" if result == "UNDECIDED" else result))
    print_performance([3], custom_three=(pattern, filter_a))


def load_filters(raw_filters):
    if not isinstance(raw_filters, dict):
        raise ValueError("filters가 객체가 아닙니다.")
    parsed = {}
    errors = {}
    for key, item in raw_filters.items():
        match = FILTER_KEY.fullmatch(key)
        if not match:
            continue
        size = int(match.group(1))
        try:
            if not isinstance(item, dict):
                raise ValueError("필터 묶음이 객체가 아닙니다.")
            normalized = {}
            for label, matrix in item.items():
                standard = normalize_label(label)
                if standard in normalized:
                    raise ValueError("중복 필터 라벨: {}".format(standard))
                normalized[standard] = validate_matrix(matrix, size, "{} / {}".format(key, label))
            if set(normalized) != {"Cross", "X"}:
                raise ValueError("Cross와 X 필터가 모두 필요합니다.")
            parsed[size] = normalized
            print("✓ {} 필터 로드 완료 (Cross, X)".format(key))
        except ValueError as exc:
            errors[size] = str(exc)
            print("✗ {} 필터 오류: {}".format(key, exc))
    return parsed, errors


def analyze_case(key, item, filters, filter_errors):
    match = CASE_KEY.fullmatch(key)
    if not match:
        raise ValueError("케이스 키는 size_N_idx 형식이어야 합니다.")
    size = int(match.group(1))
    if size in filter_errors:
        raise ValueError("필터 스키마 오류: {}".format(filter_errors[size]))
    if size not in filters:
        raise ValueError("size_{} 필터가 없습니다.".format(size))
    if not isinstance(item, dict):
        raise ValueError("패턴 항목이 객체가 아닙니다.")
    pattern = validate_matrix(item.get("input"), size, key + " / input")
    expected = normalize_label(item.get("expected"))
    score_cross = mac_2d(pattern, filters[size]["Cross"])
    score_x = mac_2d(pattern, filters[size]["X"])
    result = decide(score_cross, score_x, "Cross", "X")
    print("  Cross 점수: {!r} | X 점수: {!r}".format(score_cross, score_x))
    print("  판정: {} | expected: {} | {}".format(
        result, expected, "PASS" if result == expected else "FAIL"))
    if result == expected:
        return None
    if result == "UNDECIDED":
        return "점수 차이가 epsilon({}) 미만이어서 UNDECIDED".format(EPSILON)
    return "판정 {} ≠ expected {} (점수/데이터 확인 필요)".format(result, expected)


def json_mode(path):
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            document = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("data.json을 읽을 수 없습니다: {}".format(exc))
        return 1
    if not isinstance(document, dict) or not isinstance(document.get("patterns"), dict):
        print("JSON 스키마 오류: patterns 객체가 필요합니다.")
        return 1
    print("\n[필터 로드]")
    try:
        filters, filter_errors = load_filters(document.get("filters"))
    except ValueError as exc:
        filters, filter_errors = {}, {}
        print("필터 스키마 오류: {}".format(exc))
    failures = []
    patterns = document["patterns"]
    print("\n[패턴 분석]")
    for key, item in patterns.items():
        print("- {}".format(key))
        try:
            reason = analyze_case(key, item, filters, filter_errors)
        except ValueError as exc:
            reason = "스키마/데이터 오류: {}".format(exc)
            print("  판정: UNDECIDED | FAIL ({})".format(reason))
        if reason:
            failures.append((key, reason))
    print_performance([3, 5, 13, 25], filters=filters)
    print("\n[결과 요약]")
    print("총 테스트: {}개 | 통과: {}개 | 실패: {}개".format(
        len(patterns), len(patterns) - len(failures), len(failures)))
    failure_rate = (len(failures) / len(patterns) * 100) if patterns else 0.0
    print("실패 비율: {:.1f}%".format(failure_rate))
    if failures:
        print("실패 케이스:")
        for key, reason in failures:
            print("- {}: {}".format(key, reason))
    # A failed classification is a reported case result, not a failed program run.
    return 0


def main():
    parser = argparse.ArgumentParser(description="Mini NPU MAC 시뮬레이터")
    parser.add_argument("--mode", choices=("1", "2"), help="1=직접 입력, 2=JSON 분석")
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("data.json"),
                        help="분석할 JSON 경로 (기본: main.py 옆 data.json)")
    parser.add_argument("--generate", type=int, metavar="N",
                        help="N×N Cross와 X 패턴 생성 후 종료 (N은 3 이상의 홀수)")
    args = parser.parse_args()
    print("=== Mini NPU Simulator ===")
    if args.generate is not None:
        try:
            for label in ("Cross", "X"):
                print("\n[{} {}×{}]".format(label, args.generate, args.generate))
                for row in make_pattern(args.generate, label):
                    print(" ".join(str(value) for value in row))
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    mode = args.mode
    while mode not in ("1", "2"):
        try:
            mode = input("1. 사용자 입력 (3×3)\n2. data.json 분석\n선택: ").strip()
        except EOFError:
            raise SystemExit("모드 입력이 중단되었습니다.")
        if mode not in ("1", "2"):
            print("1 또는 2를 선택하세요.")
    return json_mode(args.data) if mode == "2" else (user_mode() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
