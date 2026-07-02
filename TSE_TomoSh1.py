#=============================================================================
# TSE_TomoSh1.py
#   [원본] 2025 한국섬유공학회지 발표 코드:
#          "얇은 쉘 구조 마네킨 메쉬의 3D프린팅 필라멘트 소모량 예측" (TSE.2025.62.319)
#   [★ NEW (this work)] 표시 부분만 이번 확장 연구에서 정정/추가한 것
#          (PLA 밀도 정정, bShellMesh 자동판정; C++ DLL은 CUDA 13.3/sm_120 재빌드).
#=============================================================================
# TomoNV example, C++ Dll version
from  cfms_tomo.shell_test.tomoSh_Cpp import *
import os

#-----------------------------------------------
#(1) specify search conditon, filename and initial orientation.
# VSCode에서 실행할 때는 .\\으로, VC++에서 디버깅할 때는 ..\\로 해야 함.
#========================================================================================================================


#DataSet= [ ('MeshData/(1)sphere.ply', 0, 0., 0)]
#DataSet= [ ('MeshData/(2)hemisphere.ply', 0, 0., 0)]
#DataSet= [ ('MeshData/(3)manikin.ply', 0, 0., 0)]
#DataSet= [ ('MeshData/(4)bodice0.ply', 0, 0, 0)]
#DataSet= [ ('MeshData/(5)bodice0.1.ply', 0, 0., 0)]
DataSet= [ ('MeshData/(6)bodice1.ply', 0, 0., 0)]
#DataSet= [ ('MeshData/(7)bodice5.ply', 0, 0, 0)]#bodice worst

# 환경변수로 입력 메쉬 교체 가능 (예: solid mesh 예제 pics/tomo_solid1.png 재생성용. pics/regen_pics.ps1 참조)
_mesh_override = os.environ.get("TOMO_MESH_FILE", "").strip()
if _mesh_override:
	DataSet = [ (_mesh_override, 0, 0., 0)]

theta_YP = 0 #type 1). seeing a specific orientation.
theta_YP = 5 #type #2). search among multiple orientations and find the optimal one, with search step 360/N (N=integer)
#========================================================================================================================

for Data in DataSet:
	(g_input_mesh_filename, Yaw, Pitch, Roll) = Data
	if( os.path.isfile(g_input_mesh_filename) ):
		if(theta_YP==0):# type 1). seeing a specific orientation.
			nYPR_Intervals=1
			yaw_range   = np.ones(nYPR_Intervals) * toRadian(Yaw)
			pitch_range = np.ones(nYPR_Intervals) * toRadian(Pitch)
			roll_range  = np.ones(nYPR_Intervals) * toRadian(Roll)
		elif(theta_YP> 0): # type 2). search optimal orientation
			nYPR_Intervals= int(360 / theta_YP) +1
			yaw_range   = np.linspace(toRadian(0), toRadian(360), num=nYPR_Intervals, endpoint=True, dtype=np.float32)
			pitch_range = np.linspace(toRadian(0), toRadian(360), num=nYPR_Intervals, endpoint=True, dtype=np.float32)
			roll_range  = np.zeros(1)
		else:
			import sys
			sys.exit(0)

		tomoSh_Cpp1 = tomoSh_Cpp(g_input_mesh_filename, nYPR_Intervals, yaw_range, pitch_range, roll_range , bVerbose=True)# load mesh file and Cpp Dll
		#-----------------------------------------------
		# (2) specify 3D printer's g-code conditions.
		tomoSh_Cpp1.wall_thickness = 0.8 # [mm]
		# ★ NEW (this work): PLA 밀도를 측정값 0.001121로 정정 (기존 0.00121, 논문 Table1 0.0121은 오타)
		tomoSh_Cpp1.PLA_density    = 0.001121 # density of PLA filament, [g/mm^3] (= 1.121 g/cm^3, ASTM E1461 측정값)
		tomoSh_Cpp1.Fclad   = 1.0 # fill ratio of cladding, always 1.0
		tomoSh_Cpp1.Fcore   = 0.15 # fill ratio of core, (0~1.0)
		tomoSh_Cpp1.Fss     = 0.2 # fill ratio of support structure, (0~1.0)
		tomoSh_Cpp1.Css     = 1.0 # correction constant for filament dilation effect.
		tomoSh_Cpp1.dVoxel  = 1.0 # size of voxel. Do not change this value.
		tomoSh_Cpp1.nVoxel  = 256 # number of voxels. Do not change this value.
		tomoSh_Cpp1.theta_c = toRadian(60.) #filament critical angle for support structure
		tomoSh_Cpp1.bUseExplicitSS = True #항상 True로 할 것.
		tomoSh_Cpp1.BedType = ( enumBedType.ebtRaft, 0., 2., 0.3 + 0.27 + 2 * 0.2)# 0, 래프트 크기(mm), 베이스 두께 + 인터페이스 두께  + 서피스 레이어 수 * 서피스 레이어 두께

		# ★ NEW (this work): bShellMesh를 watertight 여부로 자동 판정 (발표본은 False 하드코딩이었음)
		#   논문 Fig.1(c)의 보조 픽셀(alpha'/beta')은 열린 쉘에서만 필요. 닫힌 메쉬에서 True면 Vo 왜곡.
		tomoSh_Cpp1.bShellMesh = not tomoSh_Cpp1.mesh0.is_watertight # trimesh의 is_watertight는 메서드가 아니라 속성임
		# 주의: 과거 'illegal memory access'는 SetBit()의 슬롯 용량 off-by-one 오버플로우가 원인이었으며
		#       STomoVoxelSpaceInfo.cpp에서 수정되었다. 수정된 DLL로 재빌드한 뒤 사용할 것.

		tomoSh_Cpp1.Run(cpp_function_name = 'TomoSh_INT3') #call CPU/vectorized version
		#tomoSh_Cpp1.Run(cpp_function_name = 'TomoSh_CUDA') #call GPU version. Need NVIDIA graphic card (GTX760 or above)

		#-----------------------------------------------
		# (3) Rendering

		if tomoSh_Cpp1.bVerbose and os.environ.get("TOMO_NO_SHOW", "0").lower() not in ("1", "true", "yes", "on"):
			Plot3DPixels(tomoSh_Cpp1) #show pixels of the 1st optimal
			#print( tomoSh_Cpp1.Mtotal3D)
			#PrintSlotInfo( tomoSh_Cpp1, X=33,Y=38)
			#tomoSh_Cpp1.Print_table()
			#print( tomoNV_Cpp1.YPR)

		if tomoSh_Cpp1.nYPR_Intervals >= 5:
			(optimal_YPRs,worst_YPRs) = findOptimals(tomoSh_Cpp1.YPR, tomoSh_Cpp1.Mtotal3D, g_nOptimalsToDisplay) # 결과값으로부터 최적 배향 찾기
			Plot3D(tomoSh_Cpp1.mesh0, yaw_range, pitch_range, tomoSh_Cpp1.Mtotal3D, optimal_YPRs, worst_YPRs) # 찾은 최적 배향 그래프 출력.
	else:
		print( 'File Does Not Exists!!' + g_input_mesh_filename)
#-----------------------------------------------
