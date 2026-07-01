# Tomo_Shell2026

3D 프린팅 **지지구조(support structure) 부피 예측** 라이브러리 — **Tomo 시리즈의 최신 공개 버전**입니다.
**Solid mesh**와 **thin-shell mesh** 모두를 지원하며, **CPU 버전**과 **CUDA(GPU) 버전**을 제공합니다.

The latest public release of the **Tomo** series: support-structure volume prediction
for 3D printing, supporting both **solid meshes** and **thin-shell meshes**,
with **CPU and CUDA (GPU)** implementations.

> 🔗 **이전 버전(구버전) 리포지토리 / Previous versions** — 논문 인용 URL 보존을 위해 유지되며, 원본 파일은 각 리포지토리의 커밋 히스토리에서 확인할 수 있습니다:
> [tomoNV](https://github.com/cfms-lab/tomoNV) ·
> [SignedShadowCasting2021](https://github.com/cfms-lab/SignedShadowCasting2021) ·
> [Tomo_GPU2024](https://github.com/cfms-lab/Tomo_GPU2024) ·
> [Tomo_Shell2025](https://github.com/cfms-lab/Tomo_Shell2025)

---

## 설치 / Installation

Python 3.10 – 3.12 에서:

```
pip install -r "requirements(python3.10).txt"
```

> 참고
> - `open3d` 는 Python 3.12까지 지원합니다 (3.14에서 설치 실패 가능).
> - GPU(쉘) 버전은 NVIDIA 40xx에서 테스트되었고, **CUDA 13.3 + RTX 50xx (Blackwell, sm_120)** 로 재빌드·검증되었습니다 (`cfms_tomo` 참고).

---

## 발표된 논문 (2025 한국섬유공학회지) / Published papers

### `TSE_TomoSh1.py` — 얇은 쉘 구조 마네킨 메쉬의 3D프린팅 필라멘트 소모량 예측
Filament Usage Prediction in 3D Printing of Thin-Shell-Structured Manikin Mesh
· [한국섬유공학회지 2025-10, TSE.2025.62.319](http://dx.doi.org/10.12772/TSE.2025.62.319)
![sh1](pics/tomo_sh1.png)

### `TSE_TomoSh2.py` — 뼈대 구조와 군집 분석을 이용한 인체 마네킨의 최적 3D프린팅
Optimal 3D Printing of Human Manikin Using Bone Structure and Cluster Analysis
· [한국섬유공학회지 2025-12, TSE.2025.62.337](http://dx.doi.org/10.12772/TSE.2025.62.337)
![sh2](pics/tomo_sh2.png)

### `TSE_TomoSh3.py` — 뼈대 구조와 군집 분석을 이용한 사용자 정의 삼차원 인체 계측
User-Defined Three-Dimensional Human Body Measurement Using Bone Structure and Cluster Analysis
· [한국섬유공학회지 2025, TSE.2025.62.346](http://dx.doi.org/10.12772/TSE.2025.62.346)
![sh3](pics/tomo_sh3.png)

---

## 발표 이후 개선 사항 / Post-publication improvements

발표본 이후에 추가·수정된 부분은 소스코드에 **`★ NEW (this work)`** 주석으로 표시되어 있습니다.
신규 항목은 원본 함수/클래스와 **이름을 다르게** 두어(`*_v2`, `bone_p2bdist2/3`, `bone_skinweight` 등)
원본을 훼손하지 않고 전후(baseline vs. improved)를 비교할 수 있습니다.

- 예: `TSE_TomoSh3.py` 의 `USE_ROBUST` 스위치 — `False`면 발표본 그대로(baseline), `True`면 개선 버전을 실행합니다.
- 예: `TSE_TomoSh1.py` — PLA 밀도 정정(측정값 0.001121), `bShellMesh` 자동 판정(watertight).

Improvements added after publication are marked with **`★ NEW (this work)`** comments in the source.
New functions/classes use distinct names (`*_v2`, `bone_p2bdist2/3`, `bone_skinweight`, …) so that
baseline (as-published) and improved behavior can be compared side by side.

---

## 폴더 구조 / Folder structure

```
TSE_TomoSh1/2/3.py , .pdf   # 발표된 논문(2025 TSE) 스크립트/원문 — 루트
cfms_tomo/                  # 지지구조 계산 코어 (CPU / CUDA, solid & shell)
cfms_meshcut/  cfms_bodym/  # 메쉬 분할 · 인체 계측 라이브러리
highfestiva_gltfLoader/     # glTF 로더
MeshData/                   # 입력 메쉬 (.gltf/.ply 등)
pics/                       # README 그림
```

---

## 개발 안내 / Development note

이 리포지토리는 안정 버전의 **공개 스냅샷**입니다. 후속 개발은 별도 리포지토리에서 진행되며,
새 논문 발표 시점에 이 리포지토리가 갱신됩니다.

This repository is a **public snapshot** of the stable version. Active development continues
in a separate (private) repository; this snapshot is refreshed when new results are published.
