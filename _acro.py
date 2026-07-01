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
upv=m.up; rightv=m.right
gL=m.get_girth('L_armhole_girth'); gR=m.get_girth('R_armhole_girth')
def acro(verts, vec): return get_vtx_to_dir(verts, vec)
for k in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
    L = acro(gL.vertices, upv + (-rightv)*k)
    R = acro(gR.vertices, upv + ( rightv)*k)
    m.set_feature_pos('L_shoulder', L); m.set_feature_pos('R_shoulder', R)
    sw = get_pts_length(m.shortest_path(['L_shoulder','rear_neck','R_shoulder']))
    al = get_pts_length(m.shortest_path(['L_shoulder','L_elbow','L_wrist']))
    print("ACRO k=%.1f shoulder=%.2f(SK40.22) arm=%.2f(SK54.21)"%(k, sw, al))
