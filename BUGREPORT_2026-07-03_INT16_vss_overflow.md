# 버그 리포트: INT3 슬롯 z-합산 int16 오버플로 → 음수/뒤집힌 v_ss (+ CUDA 부속 이슈 2건)

작성: 2026-07-03, Tomo_SFTF_dev 프로젝트에서 전달 (SFTF 논문 G5Test 감사 중 발견).
재현 데이터·그리드 npz는 `Tomo_SFTF_dev` 저장소 커밋 `4337693` (`Experimental/G5Test/tomo_*_cache/`)에 있음.

## 요약

대형(≈10⁶ 면) 메시에서 `TomoSh_INT3`가 **음수 수백만 스케일의 v_ss**를 반환한다
(예: Group_E3_931902 1°/60° 스윕 best v_ss = −3,105,304). 원인은 슬롯(컬럼)별
z-좌표 합산 누산기가 `SLOT_BUFFER_TYPE`(**int16**, ±32,767)이어서 복잡한 컬럼에서
래핑되는 것. SFTF 논문 파이프라인에서는 "nonpositive-best 레코드 제외" 규칙이
이 값들을 걸러왔지만, 그 규칙이 걸러온 실체가 바로 이 오버플로다.

## 증상 (관측 데이터)

35개 g5test 메시 1°/60° TOMO_CPU(INT3) 스윕에서:

| 메시 | faces | int3 grid 값 범위 | 비고 |
|---|---|---|---|
| Group_E2_790253 | 1,039,452 | −3.43e5 ~ +8.11e5 | best가 음수 |
| Group_E3_931902 | 1,050,398 | −3.11e6 ~ +3.01e6 | best −3.1e6 |
| Group_E9_82675 | 916,548 | −2.60e6 ~ +2.87e6 | best가 음수 |

- v_ss(서포트 부피)는 정의상 ≥ 0이어야 함.
- 동일 메시의 CUDA 백엔드는 항상 비음수(예: E3 CUDA 0~3.6e4)이며,
  int3↔CUDA Spearman 순위상관이 E2 0.45 / E3 0.20 / E9 0.07로 붕괴 —
  두 백엔드가 사실상 다른 값을 계산 중.
- 소형 메시(수만 면 이하, 그룹 C 등)에서는 두 백엔드가 잘 일치.

## 원인 (코드 위치)

`cfms_tomo/Tomo_Shell_vc_src/`:

1. **`Tomo_types.h:33`** — `typedef short int SLOT_BUFFER_TYPE; // 2byte, ±32,767`
2. **`cpu_src/STomoSh_INT3.cpp::createVss_Implicit` (≈L931, L951)** —
   `al_sum/be_sum/TC_sum/NVB_sum/NVA_sum`이 전부 `SLOT_BUFFER_TYPE`이고
   컬럼 내 **모든 픽셀의 z-좌표를 그대로 합산**한다.
   `Vss_z = -al_sum + be_sum + TC_sum - NVB_sum + NVA_sum`.
3. **`createVoPixels` (≈L876, L891)** — 동일 구조 + `max(al_sum - be_sum, 0)`
   클램프는 래핑된 값에는 무의미(모듈러-불안전 비교).
4. **`sumType` (≈L615)** — 반환형이 `SLOT_BUFFER_TYPE`(int16). `Calculate()`가
   Va/Vb/Vnv/Vtc/Vbed를 이걸로 누산(L1173–1180).
5. `Calculate()`의 `vm_info.Vss`(FLOAT32) 자체는 넓지만, **래핑된 슬롯값**을
   65k+ 컬럼에 걸쳐 합산하므로 총합이 ±수백만으로 오염됨.

### 오버플로 성립 조건

z-인덱스 ≤ 255여도, 픽셀이 많은 컬럼에서는 z-합이 int16을 넘는다:
- 평균 z≈128 기준 **컬럼당 픽셀 ≥ ~256개**면 래핑.
- ≈10⁶ 면 메시는 256×256 XY 해상도에서 컬럼당 평균 ~15면이지만, 얇은 벽/격자/
  스캔 노이즈 부위는 국소적으로 수백 픽셀에 도달.
- **`_USE_BRIEF_SLOT_PAIRING`가 활성(Tomo_types.h:22)이라 `removeZNearPxls`
  (동일 z 중복 제거)가 건너뛰어져**(createAlBePxls의 #ifndef) 픽셀 수가 더 커짐.
- 순수 ±합은 2의 보수 모듈러 연산으로 "참값이 int16에 들어가면" 우연히 맞지만,
  al/be 짝이 안 맞는 지저분한 지오메트리(비다양체, 자기교차, 중복면)에서는
  참값 자체가 ±32,767을 넘어 슬롯 결과가 실제로 뒤집힌다. Vo의 `max(…,0)`
  클램프 경로는 래핑 시 즉시 오염.

## 수정 제안

1. 슬롯별 합산 누산기(`al_sum` 등)와 `sumType` 반환형을 **int32 이상**으로 확장
   (지역 변수라 메모리 비용 없음).
2. 슬롯 헤더(+1 Vo, +2 Vss 셀)에 int16으로 재저장하는 부분이 병목 —
   헤더 저장을 없애고 `Calculate()`에서 직접 int32/float로 합산하거나,
   슬롯 헤더용 별도 int32 배열을 두는 방안.
3. (검증용) 디버그 빌드에 `assert(|sum| < 32000)` 또는 saturation 경고 추가 —
   재발 시 조기 검출.
4. 수정 후 검증 기준: 아래 메시들에서 v_ss ≥ 0 전 그리드 + CUDA와의 Spearman
   상관 회복(소형 메시 수준인 ~0.9+ 기대). 재현 그리드는 SFTF 쪽 npz와 비교.

## 부속 이슈 (같은 dll, 별건)

### A. CUDA 백엔드 국소적 0 반환 (조용한 평가 실패)

Group_E3_931902 CUDA 1°/60° 그리드(130,321셀)에서 **정확히 0인 셀 7개**가
두 좁은 방향 근방에만 존재: (yaw 0–2°, pitch 323°)+(yaw 360°, pitch 323°;
yaw 0°와 동일 방향), (yaw 177–180°, pitch 141–145°). 이웃 셀은 정상값(28~336).
0이 grid 최솟값이 되어 "best 방향"으로 선택되는 것이 실질 피해.
결정성(재현) 여부는 SFTF 쪽에서 재스윕으로 확인 중.

### B. 대형 메시 CUDA 성능 회귀 (~130×)

동일 머신·유휴 상태·같은 밤 측정 (RTX 5080, driver 595.79, Ryzen 9 9950X3D,
Tomo_Shell2026.dll 2026-07-02 빌드, 506,368 bytes):

| 메시 | faces | CUDA 1°/60° 소요 |
|---|---|---|
| Group_E9_82675 | 916,548 | 2,084 s |
| Group_E2_790253 | 1,039,452 | 4,284 s |
| Group_E4_439142 | 1,038,714 | 12,392 s |
| Group_E3_931902 | 1,050,398 | 20,037 s |
| Group_E8_64445 | 514,938 | **27,646 s** (과거 기록 212 s → ~130×) |
| Group_E8_64445 (3°/60° 계열) | 〃 | 5개 각 ~3,082 s (매우 균일) |

면수와 무관하게 메시별 편차가 10× 이상 — 특정 지오메트리에서 CUDA 경로가
비정상적으로 느려짐. E8은 3° 스윕들이 균일(~51분)한 것으로 보아 방향당
비용 자체가 큰 상태(≈0.21 s/방향).

## 재현 방법 (SFTF 저장소에서)

```
cd Tomo_SFTF_dev
python -c "from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cpu_vss_grid; \
  import numpy as np; \
  t = compute_tomo_cpu_vss_grid(r'..\\sftf_Mesh_Data\\g5test\\Group_E3_931902.stl', \
      critical_angle=60.0, angle_step=3.0); \
  g = np.asarray(t['vss_grid']); print(g.min(), g.max())"
# 기대(버그): min이 -3e6 스케일 음수. 3° 스윕이라 ~4분 소요.
```

저장된 1° 그리드: `Tomo_SFTF_dev/Experimental/G5Test/tomo_int3_cache/Group_E3_931902_tomo_int3_1deg_60deg.npz`
(keys: yaw_values/pitch_values/vss_grid/dll_sec).
