#=============================================================================
# TSE_TomoSh3.py
#   [원본] 2025 한국섬유공학회지 발표 코드:
#          "뼈대 구조와 군집 분석을 이용한 사용자 정의 삼차원 인체 계측" (TSE.2025.62.346)
#   [★ NEW (this work)] 표시 부분은 이번 확장 연구에서 새로 추가/수정한 것.
#          상세 내용·검증은 draft_sh2/(분할 개선), draft_sh3/(강건 계측) 참조.
#=============================================================================
import os
import numpy as np
import polyscope
from cfms_bodym.WorkManager import WorkManager
from highfestiva_gltfLoader import gltfLoader
from cfms_meshcut.cut_function import cutType, CutOption
from cfms_bodym import BodyMeasure
from cfms_bodym.robust import BodyMeasureRobust
from cfms_bodym.bodym_functions import BodyPart
from cfms_meshcut.cut_function import StartTimer, EndTimer

# ────────────────────────────────────────────────────────────────────────────
# ★ NEW (this work) : 강건/개선 파이프라인 스위치  (draft_sh3)
#   True  : BodyMeasureRobust + bone_p2bdist2 (실패 격리 R1 + 허위 둘레선 기각 R2
#           + 비다양체 허용 길이 R4 + 연속 패널티 분할 bone_p2bdist2)
#   False : 원본 baseline (BodyMeasure + bone_p2bdist) — 발표본 재현/전후 비교용
# ────────────────────────────────────────────────────────────────────────────
USE_ROBUST  = os.environ.get("TSE_SH3_USE_ROBUST", "1").lower() not in ("0", "false", "no", "off")
_MeasureCls = BodyMeasureRobust    if USE_ROBUST else BodyMeasure
_p2b_ct     = cutType.bone_p2bdist2 if USE_ROBUST else cutType.bone_p2bdist
_p2b        = 'bone_p2bdist2'       if USE_ROBUST else 'bone_p2bdist'

time0 = StartTimer("Starting")

avatar = gltfLoader( # (1) GLTF 파일 열기. max_height는 mm단위. SizeKorea '키' 값.
		renderer = polyscope,
		filename = 'MeshData/SK6th_F20_4k_NoFinger.gltf',		max_height = 165.001,
		#filename = 'MeshData/SK6th_F20_10k_NoFinger.gltf',	max_height = 165.001,
		#filename = 'MeshData/SK6th_M20_4k_NoFinger.gltf',		max_height = 175.99,
		#filename = 'MeshData/SK6th_M20_4k_NoFinger_JumpDown.gltf',		max_height = 175.99,
		#filename = 'MeshData/SK6th_M20_87k_NoFinger.gltf',	max_height = 175.99,
		)

manager = WorkManager( # (2) 메쉬 분할
	avatar = avatar,
	cut_options = [
		CutOption( 'kmeans/5',			cutType.kmeans, 5),  				#optional
		CutOption( 'kmedoids/5',		cutType.KMedoids, 5),				#optional
		CutOption( 'aggler5',				cutType.aggler, 5),					#optional
		CutOption( 'bone_pairdist',	cutType.bone_pairdist, 6),	#필수. 여기서 Torso 가져다 쓴다
		CutOption( _p2b, 	_p2b_ct, 6)],	#필수. 여기서 6개 bodypart 갖다 쓴다. (USE_ROBUST에 따라 p2bdist/p2bdist2)
	)

body_parts = manager.getBodyParts([ # (3) 계측용으로 아바타의 조각들을 모은다.
  	['bone_pairdist',	BodyPart.Head,			BodyPart.Torso], #'bone_pairdist'의 Head는 이름을 Torso로 구분해서 목/겨드랑이 분리용으로 추가로 가져온다.
		[_p2b,	BodyPart.Head,			None],
		[_p2b,	BodyPart.Bodice, 		None],
		[_p2b,	BodyPart.LeftArm, 	None],
		[_p2b,	BodyPart.RightArm, 	None],
		[_p2b,	BodyPart.LeftLeg, 	None],
		[_p2b,	BodyPart.RightLeg, 	None]
	])

bodym			= _MeasureCls( avatar, body_parts, # (4) 인체 계측 (USE_ROBUST에 따라 BodyMeasure/BodyMeasureRobust)
		manager.works[0].bodym#최종 계측일 때는 BodyPart 이름 검사 패스.
  )
bodym.measure()

EndTimer(time0, "Ending")

# (5) 렌더링
avatar.add_to(polyscope)
manager.layout2D() # body들을 겹치지 않게 좌우로 이동시킴
manager.add_to(polyscope)
bodym.add_to(polyscope)
save_path = os.environ.get("TOMO_SCREENSHOT", "").strip()
if save_path:
	os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
	try:
		polyscope.set_window_size(
			int(os.environ.get("TOMO_SCREENSHOT_W", "1920")),
			int(os.environ.get("TOMO_SCREENSHOT_H", "768")),
		)
	except Exception:
		pass
	bounds = np.array([
		np.minimum(avatar.tmesh.bounds[0], manager.bounds[0]),
		np.maximum(avatar.tmesh.bounds[1], manager.bounds[1]),
	])
	center = bounds.mean(axis=0)
	span = float(np.linalg.norm(bounds[1] - bounds[0]))
	camera_distance = float(os.environ.get("TOMO_CAMERA_DISTANCE", "2.1"))
	camera_z_offset = float(os.environ.get("TOMO_CAMERA_Z_OFFSET", "0.02"))
	camera_view = os.environ.get("TOMO_CAMERA_VIEW", "front").strip().lower()
	camera_views = {
		"front": np.array([1., 0., 0.]),
		"back": np.array([-1., 0., 0.]),
		"left": np.array([0., -1., 0.]),
		"right": np.array([0., 1., 0.]),
		"side": np.array([0., -1., 0.]),
	}
	camera_direction = camera_views.get(camera_view, camera_views["front"])
	camera_direction = camera_direction / np.linalg.norm(camera_direction)
	camera_up = np.array([0., 0., 1.])
	camera_right = np.cross(camera_up, camera_direction)
	camera_right = camera_right / np.linalg.norm(camera_right)
	camera_shift = float(os.environ.get("TOMO_CAMERA_SHIFT", "1.2"))
	camera_target = center + camera_right * camera_shift * span
	camera_position = camera_target + camera_direction * camera_distance * span + camera_up * camera_z_offset * span
	polyscope.set_ground_plane_mode(os.environ.get("TOMO_GROUND_PLANE", "none"))
	polyscope.set_view_projection_mode("orthographic")
	polyscope.look_at(
		(float(camera_position[0]), float(camera_position[1]), float(camera_position[2])),
		(float(camera_target[0]), float(camera_target[1]), float(camera_target[2])),
	)
	polyscope.set_SSAA_factor(int(os.environ.get("TOMO_SSAA", "3")))
	polyscope.screenshot(save_path, transparent_bg=False)
	print("wrote", save_path)

if os.environ.get("TOMO_NO_SHOW", "0").lower() not in ("1", "true", "yes", "on"):
	polyscope.show()
