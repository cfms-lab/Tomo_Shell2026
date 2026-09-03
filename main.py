"""Tomo_Shell2026 — support-structure volume prediction for 3D printing.

이 리포지토리는 별도의 진입점 없이 세 개의 예제 스크립트를 직접 실행합니다.
이 파일은 그 안내만 출력합니다. (자세한 사용법: README.md)
"""

SCRIPTS = [
    ("TSE_TomoSh1.py", "쉘·solid 메쉬 최적 배향, 필라멘트 소모량 예측 (TSE.2025.62.319)"),
    ("TSE_TomoSh2.py", "뼈대·군집 분석 기반 마네킨 최적 3D 프린팅 (TSE.2025.62.337)"),
    ("TSE_TomoSh3.py", "뼈대 기반 사용자 정의 인체 계측 (TSE.2025.62.346)"),
]


def main():
    print("Tomo_Shell2026 — support-structure volume prediction for 3D printing")
    print("실행할 스크립트를 골라 직접 실행하세요. 예) python TSE_TomoSh1.py")
    for name, desc in SCRIPTS:
        print(f"  {name:16s} {desc}")
    print("자세한 사용법: README.md")


if __name__ == "__main__":
    main()
