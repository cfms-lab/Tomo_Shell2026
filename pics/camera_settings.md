# pics 카메라 설정값 (2026-07-02 재생성 기준)

모든 그림은 소스코드에 내장된 헤드리스 렌더링 경로(환경변수)로 생성한다.
아래 값은 생성 당시 사용된 값(=코드 기본값)이며, 코드 기본값이 바뀌어도 동일한 그림을
얻을 수 있도록 [regen_pics.ps1](regen_pics.ps1)에 명시적으로 고정되어 있다.

## 공통

| 환경변수 | 값 | 의미 |
|---|---|---|
| `TOMO_NO_SHOW` | `1` | 창/브라우저를 띄우지 않음 (headless) |

## tomo_sh1.png — TSE_TomoSh1.py (matplotlib Plot3D)

| 환경변수 | 값 | 의미 |
|---|---|---|
| `TOMO_PLOT3D_SAVE` | `pics/tomo_sh1.png` | Plot3D figure 저장 경로 |
| `TOMO_PLOT3D_DPI` | `100` | 저장 DPI (figsize 12×8 → 1200×800 px) |

- 3D 카메라: matplotlib 기본 시점(elev=30°, azim=-60°). 별도 설정 없음.
- 그림 내용(최적 배향 수치)은 카메라가 아니라 계산 파라미터(PLA 밀도, bShellMesh 등)에 따라 달라짐.

## tomo_solid1.png — TSE_TomoSh1.py + Bunny_69k.stl (solid mesh 예제)

tomo_sh1.png과 동일한 설정에 입력 메쉬만 교체:

| 환경변수 | 값 | 의미 |
|---|---|---|
| `TOMO_MESH_FILE` | `MeshData/Bunny_69k.stl` | 입력 메쉬 오버라이드 (닫힌 solid 메쉬) |
| `TOMO_PLOT3D_SAVE` | `pics/tomo_solid1.png` | Plot3D figure 저장 경로 |
| `TOMO_PLOT3D_DPI` | `100` | 저장 DPI |

- `bShellMesh`는 watertight 자동판정으로 `False`(solid)가 된다. 코드 수정 불필요.

## tomo_sh2.png — TSE_TomoSh2.py (polyscope)

| 환경변수 | 값 | 의미 |
|---|---|---|
| `TOMO_SCREENSHOT` | `pics/tomo_sh2.png` | 스크린샷 저장 경로 |
| `TOMO_SCREENSHOT_W` / `TOMO_SCREENSHOT_H` | `1920` / `768` | 창(이미지) 크기 |
| `TOMO_CAMERA_VIEW` | `front` | 시선 방향 (+X에서 원점 방향, up=+Z) |
| `TOMO_CAMERA_DISTANCE` | `2.6` | 카메라 거리 (장면 span 배수) |
| `TOMO_CAMERA_SHIFT` | `1.6` | 타깃을 camera_right 방향으로 이동 (span 배수) |
| `TOMO_CAMERA_Z_OFFSET` | `0.04` | 카메라 높이 오프셋 (span 배수) |
| `TOMO_GROUND_PLANE` | `none` | 바닥면 표시 안 함 |
| `TOMO_SSAA` | `3` | 안티앨리어싱 배수 |

- 투영: orthographic (코드에서 고정).
- 조각 배치: `Batch.layout2D()`가 결정적(cut_options 순서대로 +X 방향 나열)이므로 별도 설정 불필요.
- 저장 후 [crop_margins.py](crop_margins.py)로 흰 여백을 잘라낸다 (패딩 24px, regen_pics.ps1이 자동 호출).

## tomo_sh3.png — TSE_TomoSh3.py (polyscope)

sh2와 동일한 환경변수 체계. 값만 다름:

| 환경변수 | 값 |
|---|---|
| `TOMO_SCREENSHOT` | `pics/tomo_sh3.png` |
| `TOMO_SCREENSHOT_W` / `TOMO_SCREENSHOT_H` | `1920` / `768` |
| `TOMO_CAMERA_VIEW` | `front` |
| `TOMO_CAMERA_DISTANCE` | `2.1` |
| `TOMO_CAMERA_SHIFT` | `1.2` |
| `TOMO_CAMERA_Z_OFFSET` | `0.02` |
| `TOMO_GROUND_PLANE` | `none` |
| `TOMO_SSAA` | `3` |

sh3도 저장 후 crop_margins.py로 여백을 잘라낸다.

## 재생성 방법

프로젝트 루트에서:

```powershell
.\pics\regen_pics.ps1           # 네 장 모두
.\pics\regen_pics.ps1 solid1    # 특정 그림만 (sh1 | sh2 | sh3 | solid1)
```
