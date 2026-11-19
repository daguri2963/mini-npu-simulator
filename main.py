"""숫자 배열에서 십자가(Cross)와 X를 구별하는 콘솔 프로그램.

실행: python main.py
코드를 읽을 때는 make_pattern → mac_2d → decide → user_mode/json_mode 순서가 쉽다.
"""

# import는 다른 파일이나 파이썬 표준 라이브러리의 기능을 가져온다.
import argparse
import json       # data.json을 파이썬 딕셔너리와 리스트로 읽는다.
import math       # 숫자가 무한대나 NaN인지 검사한다.
import re         # size_5_1 같은 키의 글자 형식을 확인한다.
import time       # MAC 실행 시간을 잰다.
from pathlib import Path


EPSILON = 1e-9  # 두 점수의 차이가 이 값보다 작으면 사실상 동점으로 본다.
REPEATS = 10  # 과제의 최소 기준: 각 크기와 구현마다 MAC을 10회 호출한다.
# 정규식의 \d+는 숫자 한 개 이상, \Z는 문자열의 끝을 뜻한다.
CASE_KEY = re.compile(r"size_(\d+)_(\d+)\Z")
FILTER_KEY = re.compile(r"size_(\d+)\Z")


def make_pattern(size, label):
    """홀수 size를 받아 Cross 또는 X 모양의 2차원 리스트를 반환한다."""
    if size < 3 or size % 2 == 0 or label not in ("Cross", "X"):
        raise ValueError("패턴 크기는 3 이상의 홀수이고 라벨은 Cross/X여야 합니다.")
    middle = size // 2  # //는 나눗셈의 몫이다. 5//2는 가운데 인덱스 2다.
    pattern = []
    for r in range(size):  # r은 행 번호: 0, 1, ..., size-1
        row = []
        for c in range(size):  # c는 열 번호
            if label == "Cross":
                filled = r == middle or c == middle
            else:
                # 왼쪽 위↘오른쪽 아래, 오른쪽 위↙왼쪽 아래 대각선
                filled = r == c or r + c == size - 1
            row.append(1 if filled else 0)
        pattern.append(row)
    return pattern


def validate_matrix(value, size, name):
    """value가 size×size 숫자 배열인지 검사하고, 맞으면 그대로 반환한다."""
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("{}: {}개 행이 필요합니다.".format(name, size))
    # enumerate(..., 1)은 첫 행을 사람이 읽는 번호인 1행부터 센다.
    for row_number, row in enumerate(value, 1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("{}: {}행에 {}개 열이 필요합니다.".format(name, row_number, size))
        for item in row:
            # bool도 파이썬에서는 int의 하위 유형이므로 따로 제외한다.
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                raise ValueError("{}: 유한한 숫자만 허용합니다.".format(name))
    return value


def mac_2d(pattern, filter_matrix):
    """두 2차원 배열의 같은 위치를 곱해 모두 더한 점수를 반환한다."""
    score = 0.0
    for r in range(len(pattern)):
        for c in range(len(pattern[r])):
            # 예: pattern[1][2]와 filter_matrix[1][2]를 곱한다.
            score += pattern[r][c] * filter_matrix[r][c]
    # 0×0은 0이므로 빈칸끼리 일치해도 점수가 늘지는 않는다.
    return score


def flatten(matrix):
    """[[a, b], [c, d]]를 [a, b, c, d]처럼 한 줄로 펼친다."""
    flat = []
    for row in matrix:
        for item in row:
            flat.append(item)
    return flat


def mac_1d(pattern, filter_matrix):
    """펼친 1차원 배열에서 같은 인덱스의 값을 곱해 더한다."""
    score = 0.0
    for i in range(len(pattern)):
        score += pattern[i] * filter_matrix[i]
    return score


def decide(score_a, score_b, label_a="A", label_b="B"):
    """두 점수를 비교해 높은 쪽의 이름 또는 UNDECIDED를 반환한다."""
    # abs는 절댓값이다. 0.9와 0.8999999999999999의 작은 오차를 무시한다.
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    if score_a > score_b:
        return label_a
    return label_b


def normalize_label(value):
    """JSON의 +/cross/x를 프로그램 안에서 쓸 Cross/X로 통일한다."""
    if not isinstance(value, str):
        raise ValueError("라벨은 문자열이어야 합니다.")
    labels = {"+": "Cross", "cross": "Cross", "x": "X"}
    # strip은 앞뒤 공백 제거, lower는 영문 소문자 변환이다.
    result = labels.get(value.strip().lower())
    if result is None:
        raise ValueError("알 수 없는 라벨: {!r}".format(value))
    return result


def read_matrix(name, size=3):
    """콘솔에서 숫자 size개씩 size줄을 읽고, 틀린 줄은 다시 받는다."""
    print("{} ({}줄, 줄마다 {}개 숫자; 첫 줄에 @Cross 또는 @X 입력 시 자동 생성):".format(
        name, size, size))
    rows = []  # 입력을 마친 행만 여기에 저장한다.
    while len(rows) < size:
        try:
            # input은 한 줄을 문자열로 읽고, split은 공백으로 나눈다.
            parts = input("  {}행> ".format(len(rows) + 1)).split()
        except EOFError:
            raise SystemExit("입력이 중단되었습니다.")
        # 첫 줄의 @Cross/@X는 숫자를 직접 입력하는 대신 생성기를 사용한다.
        if not rows and len(parts) == 1 and parts[0].lower() in ("@cross", "@x"):
            label = normalize_label(parts[0][1:])
            print("{} {}×{} 패턴 자동 생성 완료".format(label, size, size))
            return make_pattern(size, label)
        if len(parts) != size:
            print("입력 형식 오류: 각 줄에 {}개의 숫자를 공백으로 구분해 입력하세요.".format(size))
            continue
        try:
            # 입력은 문자열이므로 float로 바꾼 다음 유한한 숫자인지 확인한다.
            row = [float(part) for part in parts]
            if not all(math.isfinite(x) for x in row):
                raise ValueError
        except ValueError:
            print("입력 형식 오류: 유한한 숫자만 입력하세요.")
            continue
        # continue는 현재 반복을 다시 시작한다. 성공한 행만 append로 저장된다.
        rows.append(row)
    return rows


def benchmark(matrix, filter_matrix, repeats=REPEATS):
    """2D와 1D MAC을 각각 repeats회 실행해 평균 시간(ms) 두 개를 반환한다.

    파일 읽기, 입력, 출력과 1D 변환은 타이머 밖에서 처리한다. 아주 짧은
    호출에는 타이머/반복문 비용과 시스템 부하가 섞이므로 수치는 참고값이다.
    """
    if repeats < 10:
        raise ValueError("성능 측정은 최소 10회 반복해야 합니다.")
    # 1D 변환은 시간을 재기 전에 한다. 두 방식 모두 같은 원본 배열을 쓴다.
    flat_matrix = flatten(matrix)
    flat_filter = flatten(filter_matrix)
    timings = []
    # 튜플 하나는 (실행할 함수, 패턴, 필터)다. 먼저 2D, 다음에 1D를 잰다.
    for function, left, right in (
        (mac_2d, matrix, filter_matrix),
        (mac_1d, flat_matrix, flat_filter),
    ):
        start = time.perf_counter_ns()  # ns(나노초) 단위 시작 시각
        for _ in range(repeats):
            # _는 반복 횟수만 필요하고 순서 번호는 사용하지 않는다는 관례다.
            function(left, right)
        # 총 ns / 호출 횟수 / 1,000,000 = 호출당 평균 ms(밀리초)
        timings.append((time.perf_counter_ns() - start) / repeats / 1_000_000)
    return timings


def print_performance(sizes, filters=None, custom_three=None):
    """요청받은 크기의 2D/1D 평균 시간과 N² 곱셈 횟수를 표로 출력한다."""
    print("\n[성능 분석] MAC 함수 호출 평균 / {}회".format(REPEATS))
    print("{:>8} {:>14} {:>14} {:>12}".format("크기", "2D (ms)", "1D (ms)", "연산 횟수"))
    for size in sizes:
        if size == 3 and custom_three is not None:
            # 직접 입력 모드에서는 사용자가 넣은 3×3 배열로 측정한다.
            pattern, filter_matrix = custom_three
        else:
            # JSON 모드의 3×3은 파일에 없으므로 자동 생성 패턴을 쓴다.
            pattern = make_pattern(size, "Cross")
            filter_matrix = filters.get(size, {}).get("Cross") if filters else None
            if filter_matrix is None:
                filter_matrix = make_pattern(size, "Cross")
        two_d, one_d = benchmark(pattern, filter_matrix)
        # N×N 배열에서 각 위치를 한 번씩 곱하므로 곱셈 횟수는 size*size다.
        print("{:>3}×{:<4} {:>14.6f} {:>14.6f} {:>12}".format(size, size, two_d, one_d, size * size))
    print("※ 변환과 입출력 시간 제외. 1D 변환 비용은 별도입니다.")


def user_mode():
    """사용자에게 3×3 배열 세 개를 받아 A/B 점수와 판정을 보여준다."""
    print("\n[필터 입력]")
    filter_a = read_matrix("필터 A")
    filter_b = read_matrix("필터 B")
    print("필터 A/B 저장 완료 (각 3×3)")
    print("\n[패턴 입력]")
    pattern = read_matrix("패턴")
    score_a = mac_2d(pattern, filter_a)
    score_b = mac_2d(pattern, filter_b)
    # 여기서는 이름이 A/B다. 같은 decide를 JSON 모드에서는 Cross/X로 쓴다.
    result = decide(score_a, score_b)
    print("\n[MAC 결과]")
    print("A 점수: {!r}".format(score_a))
    print("B 점수: {!r}".format(score_b))
    print("판정: {}".format("판정 불가 (UNDECIDED)" if result == "UNDECIDED" else result))
    print_performance([3], custom_three=(pattern, filter_a))


def load_filters(raw_filters):
    """JSON filters를 크기별 Cross/X 배열로 바꾸고 오류도 따로 모은다."""
    if not isinstance(raw_filters, dict):
        raise ValueError("filters가 객체가 아닙니다.")
    parsed = {}  # 예: {5: {"Cross": [[...]], "X": [[...]]}}
    errors = {}  # 예: {5: "5행에 5개 열이 필요합니다."}
    for key, item in raw_filters.items():
        # fullmatch는 키 전체가 size_숫자 형태인지 확인한다.
        match = FILTER_KEY.fullmatch(key)
        if not match:
            continue
        size = int(match.group(1))  # size_13에서 문자열 "13"을 정수 13으로
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
            # 필터 하나가 잘못되어도 전체 분석을 중단하지 않는다.
            errors[size] = str(exc)
            print("✗ {} 필터 오류: {}".format(key, exc))
    return parsed, errors


def analyze_case(key, item, filters, filter_errors):
    """JSON 패턴 한 건을 검증·판정한다. 통과하면 None, 실패하면 이유를 반환한다."""
    match = CASE_KEY.fullmatch(key)
    if not match:
        raise ValueError("케이스 키는 size_N_idx 형식이어야 합니다.")
    size = int(match.group(1))  # size_5_2에서 5를 가져와 5×5 필터를 선택
    if size in filter_errors:
        raise ValueError("필터 스키마 오류: {}".format(filter_errors[size]))
    if size not in filters:
        raise ValueError("size_{} 필터가 없습니다.".format(size))
    if not isinstance(item, dict):
        raise ValueError("패턴 항목이 객체가 아닙니다.")
    pattern = validate_matrix(item.get("input"), size, key + " / input")
    expected = normalize_label(item.get("expected"))
    # 패턴과 두 필터의 MAC 점수를 각각 구한다.
    score_cross = mac_2d(pattern, filters[size]["Cross"])
    score_x = mac_2d(pattern, filters[size]["X"])
    result = decide(score_cross, score_x, "Cross", "X")
    print("  Cross 점수: {!r} | X 점수: {!r}".format(score_cross, score_x))
    print("  판정: {} | expected: {} | {}".format(
        result, expected, "PASS" if result == expected else "FAIL"))
    if result == expected:
        return None
    # 동점으로 실패했는지, 다른 라벨을 골라 실패했는지 구분한다.
    if result == "UNDECIDED":
        return "점수 차이가 epsilon({}) 미만이어서 UNDECIDED".format(EPSILON)
    return "판정 {} ≠ expected {} (점수/데이터 확인 필요)".format(result, expected)


def json_mode(path):
    """파일의 모든 패턴을 분석하고 각 결과·성능·전체 요약을 출력한다."""
    try:
        # with는 파일 사용이 끝나면 자동으로 닫는다. utf-8-sig는 BOM도 허용한다.
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
    # items()는 (케이스 키, 케이스 내용)을 하나씩 꺼낸다.
    for key, item in patterns.items():
        print("- {}".format(key))
        try:
            reason = analyze_case(key, item, filters, filter_errors)
        except ValueError as exc:
            # 한 케이스의 오류는 FAIL로 적고 다음 케이스로 계속한다.
            reason = "스키마/데이터 오류: {}".format(exc)
            print("  판정: UNDECIDED | FAIL ({})".format(reason))
        if reason:
            failures.append((key, reason))
    # 모든 케이스 처리 후 성능 측정과 결과 요약을 출력한다.
    print_performance([3, 5, 13, 25], filters=filters)
    print("\n[결과 요약]")
    print("총 테스트: {}개 | 통과: {}개 | 실패: {}개".format(
        len(patterns), len(patterns) - len(failures), len(failures)))
    # 패턴이 0개일 때 0으로 나누는 오류를 피한다.
    failure_rate = (len(failures) / len(patterns) * 100) if patterns else 0.0
    print("실패 비율: {:.1f}%".format(failure_rate))
    if failures:
        print("실패 케이스:")
        for key, reason in failures:
            print("- {}: {}".format(key, reason))
    # 케이스의 FAIL은 보고서의 결과다. 파일 분석 자체는 정상 종료했다.
    return 0


def main():
    """명령줄 옵션을 읽고 패턴 생성/직접 입력/JSON 분석 중 하나를 실행한다."""
    # argparse는 --mode, --data 같은 명령줄 옵션을 처리한다.
    parser = argparse.ArgumentParser(description="Mini NPU MAC 시뮬레이터")
    parser.add_argument("--mode", choices=("1", "2"), help="1=직접 입력, 2=JSON 분석")
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("data.json"),
                        help="분석할 JSON 경로 (기본: main.py 옆 data.json)")
    parser.add_argument("--generate", type=int, metavar="N",
                        help="N×N Cross와 X 패턴 생성 후 종료 (N은 3 이상의 홀수)")
    args = parser.parse_args()
    print("=== Mini NPU Simulator ===")
    if args.generate is not None:
        # --generate N은 다른 모드를 실행하지 않고 두 기본 패턴만 출력한다.
        try:
            for label in ("Cross", "X"):
                print("\n[{} {}×{}]".format(label, args.generate, args.generate))
                for row in make_pattern(args.generate, label):
                    print(" ".join(str(value) for value in row))
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    mode = args.mode
    # --mode를 생략했다면 사용자가 1 또는 2를 고를 때까지 반복한다.
    while mode not in ("1", "2"):
        try:
            mode = input("1. 사용자 입력 (3×3)\n2. data.json 분석\n선택: ").strip()
        except EOFError:
            raise SystemExit("모드 입력이 중단되었습니다.")
        if mode not in ("1", "2"):
            print("1 또는 2를 선택하세요.")
    if mode == "2":
        return json_mode(args.data)
    user_mode()
    return 0


# 직접 python main.py로 실행할 때만 main()을 호출한다.
# 다른 파일이 import main을 하면 테스트에서 함수만 가져다 쓸 수 있다.
if __name__ == "__main__":
    raise SystemExit(main())
