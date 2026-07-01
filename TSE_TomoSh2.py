#=============================================================================
# TSE_TomoSh2.py
#   [원본] 2025 한국섬유공학회지 발표 코드:
#          "뼈대 구조와 군집 분석을 이용한 인체 마네킨의 최적 3D프린팅" (TSE.2025.62.337)
#   이 파일은 발표본 그대로이며 이번 확장 연구의 변경 사항이 없다(★ NEW 없음).
#   (인체 '계측' 파이프라인 및 그 개선은 TSE_TomoSh3.py / draft_sh2 / draft_sh3 참조.)
#=============================================================================
import numpy as np
import os
import polyscope #3D renderer by Nicholas Sharp. https://polyscope.run/py/

from cfms_meshcut.cut_batchWorks import Batch
from cfms_meshcut.cut_function import cutType, CutOption
from cfms_tomo.tomo_slicingOptions import SlicingOptions, enumBedType
from highfestiva_gltfLoader import gltfLoader #modified from https://github.com/highfestiva/gltf-skin-anim-viewer

# (0). global options
s_o = SlicingOptions() #default 3D printer options
s_o.bVerbose    = True		#print debug informations
s_o.bUseCUDA    = False		#use GPU for optimal orientation search
s_o.bUseCUDA    = os.environ.get("TOMO_USE_CUDA", str(int(s_o.bUseCUDA))).lower() not in ("0", "false", "no", "off")
s_o.bShellMesh  = True  	#non-closed triangle soups
s_o.bShellMesh  = os.environ.get("TOMO_SHELL_MESH", str(int(s_o.bShellMesh))).lower() not in ("0", "false", "no", "off")
s_o.ShellThickness = 0.	#shell thickness [mm]
s_o.ShellThickness = float(os.environ.get("TOMO_SHELL_THICKNESS", s_o.ShellThickness))
s_o.RenderShellThickness = float(os.environ.get("TOMO_RENDER_SHELL_THICKNESS", s_o.ShellThickness))
s_o.theta_YP 		= 10		#optimal orientation search angle step (= 360/N). the smaller, the slower.
s_o.theta_YP 		= int(os.environ.get("TOMO_THETA_YP", s_o.theta_YP))
bed_type_override = os.environ.get("TOMO_BED_TYPE", "").strip().lower()
if bed_type_override:
    bed_types = {
        "none": enumBedType.ebtNone,
        "brim": enumBedType.ebtBrim,
        "raft": enumBedType.ebtRaft,
        "skirt": enumBedType.ebtSkirt,
    }
    if bed_type_override not in bed_types:
        raise ValueError(f"Unknown TOMO_BED_TYPE={bed_type_override!r}")
    s_o.BedType = (bed_types[bed_type_override],) + tuple(s_o.BedType[1:])

# (1). Load raw mesh data
avatar = gltfLoader(
    renderer = polyscope,
    max_height = 170.,# [mm]
		#filename = 'MeshData/masha1_2Finger_JumpingDown.gltf'
		#filename = 'MeshData/masha1_NoFinger_JumpingDown_rest.gltf'
  	filename = 'MeshData/SK6th_F20_4k_NoFinger.gltf'
  	)

avatar.add_to(polyscope)

# (2). mesh clustering
nc		= CutOption( '0_NoCut',	cutType.no_cut , 0)#no cutting

db2		= CutOption( 'DBSCAN_2',	cutType.DBSCAN, 2.)
db5		= CutOption( 'DBSCAN_5',	cutType.DBSCAN, 5.)
db10	= CutOption( 'DBSCAN_10',	cutType.DBSCAN, 10.)
db20	= CutOption( 'DBSCAN_20',	cutType.DBSCAN, 20.)

km2		= CutOption( 'kmeans_2',	cutType.kmeans, 2)
km5		= CutOption( 'kmeans_5',	cutType.kmeans, 5)
km10	= CutOption( 'kmeans_10',	cutType.kmeans,10)
km20	= CutOption( 'kmeans_20',	cutType.kmeans,20)

ag2		= CutOption( 'aggl_2', 		cutType.aggler, 2)
ag5		= CutOption( 'aggl_5', 		cutType.aggler, 5)
ag10	= CutOption( 'aggl_10', 	cutType.aggler,10)
ag20	= CutOption( 'aggl_20', 	cutType.aggler,20)

kd2		= CutOption( 'KMedoids_2',  cutType.KMedoids, 2)
kd5		= CutOption( 'KMedoids_5',  cutType.KMedoids, 5)
kd10	= CutOption( 'KMedoids_10', cutType.KMedoids,10)
kd20	= CutOption( 'KMedoids_20', cutType.KMedoids,20)

# bone-based
bn1		= CutOption( 'bone1_kmeans', 		cutType.bone_kmeans, 0)
bn2		= CutOption( 'bone2_kM3doids', 	cutType.bone_KMedoids, 0)
bn3		= CutOption( 'bone3_pairdist', 	cutType.bone_pairdist, 0)#젤 이쁨
bn4		= CutOption( 'bone4_p2bdist', 	cutType.bone_p2bdist, 0)#등간격

cut_option_sets = {
	"all": [nc, kd20, bn1, bn2, bn3, bn4],
	"nc": [nc],
	"kd20": [kd20],
	"bn1": [bn1],
	"bn2": [bn2],
	"bn3": [bn3],
	"bn4": [bn4],
}
selected_cut_options = cut_option_sets.get(os.environ.get("TOMO_CUT_OPTIONS", "all"), cut_option_sets["all"])

batch = Batch(
	avatar = avatar,
	#cut_options = [db2, db5, db10, db20],
	#cut_options = [km2, km2, km10, km20],
	#cut_options = [ag2, ag5, ag10, ag20],
	#cut_options = [kd2, kd5, kd10, kd20],
	#cut_options = [db5, km2, ag20, kd20],
	#cut_options = [bn1, bn2, bn3],
	cut_options = selected_cut_options,
	# cut_options = [bn4],
	slicing_option = s_o
	)

batch.GetMss()

#batch.save_obj() #save cut parts as wavefront .obj file

batch.add_to(polyscope)

# (3). final rendering
if os.environ.get("TOMO_NO_SHOW", "0").lower() not in ("1", "true", "yes", "on"):
	polyscope.show()
