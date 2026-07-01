import numpy as np, polyscope
from cfms_bodym.WorkManager import WorkManager
from highfestiva_gltfLoader import gltfLoader
from cfms_meshcut.cut_function import cutType, CutOption
from cfms_bodym import BodyMeasure
from cfms_bodym.bodym_functions import BodyPart, get_vtx_to_dir, get_pts_length
av=gltfLoader(renderer=polyscope, filename='MeshData/SK6th_F20_4k_NoFinger.gltf', max_height=165.001)
mgr=WorkManager(avatar=av,cut_options=[CutOption('bp',cutType.bone_pairdist,6),CutOption('bone_p2bdist',cutType.bone_p2bdist,6)])
bp=mgr.getBodyParts([['bp',BodyPart.Head,BodyPart.Torso],['bone_p2bdist',BodyPart.Head,None],['bone_p2bdist',BodyPart.Bodice,None],['bone_p2bdist',BodyPart.LeftArm,None],['bone_p2bdist',BodyPart.RightArm,None],['bone_p2bdist',BodyPart.LeftLeg,None],['bone_p2bdist',BodyPart.RightLeg,None]])
m=BodyMeasure(av,bp,mgr.works[0].bodym); m.measure()
up=m.up; right=m.right
torso=m.getBP(BodyPart.Torso); bodice=m.getBP(BodyPart.Bodice)
src = torso if torso is not None else bodice
V = np.array(src.tmesh.vertices)
for k in [0.5,1.0,1.5,2.0,2.5,3.0,4.0]:
    L = get_vtx_to_dir(V, up + (-right)*k); R = get_vtx_to_dir(V, up + (right)*k)
    m.set_feature_pos('L_shoulder', L); m.set_feature_pos('R_shoulder', R)
    sw=get_pts_length(m.shortest_path(['L_shoulder','rear_neck','R_shoulder']))
    al=get_pts_length(m.shortest_path(['L_shoulder','L_elbow','L_wrist']))
    print("ACRO2 k=%.1f shoulder=%.2f(40.22) arm=%.2f(54.21)"%(k,sw,al))
