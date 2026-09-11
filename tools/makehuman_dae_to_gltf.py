"""[폐기됨 — 쓰지 말 것] MakeHuman Collada -> Mixamo 표기 skinned glTF

**이 경로는 작동하지 않는다.** `tools/makehuman_dae_to_rig.py` 를 쓴다.
보존하는 이유는 무엇을 시도했고 왜 실패했는지가 다음 사람에게 필요해서다.

glTF 로 넘기면 `highfestiva_gltfLoader` 의 규약 넷을 전부 맞춰야 한다 —
skin 이 애니메이션 루프 안에서만 읽히고, 정지 자세 변환이 계산되지 않으며,
쿼터니언 성분 순서가 어긋나고(glTF x,y,z,w 대 PyGLM w,x,y,z), 축·배율 규약이
스키닝·역바인드행렬과 얽혀 있다. 앞의 둘은 고쳤지만 쿼터니언 쪽은 고치면
**기준 메쉬의 뼈대가 오히려 뒤집힌다**(머리 0.32, 발 0.72) — 로더가 그 오독을
전제로 맞춰져 있기 때문이다. 결국 이 스크립트로 만든 파일에서는 관절이 키의
0.47 한 점에 뭉쳤다.

파이프라인이 실제로 쓰는 것은 메쉬와 이름 붙은 뼈 위치뿐이므로, glTF 를 거치지
않고 그 둘만 넘기는 편이 옳다. 그것이 makehuman_dae_to_rig.py 다.

--- 아래는 원래 문서 ---

MakeHuman 번들 Collada 내보내기가 만든 리그 메쉬를 이 리포의 계측 파이프라인이
읽을 수 있는 형태로 바꾼다. 파이프라인은 뼈대를 **이름으로** 찾으므로
(`hf_manager.get_end_bone_pos` 가 `mixamorig:*` 를 부른다) cmu_mb 표기를 Mixamo
표기로 옮기는 것이 이 스크립트의 핵심이다.

cmu_mb 를 고른 이유: 번들 리그 넷 중 이름이 Mixamo 와 사실상 같다.
`default` 는 163개 뼈에 `upperarm01.L` 식 표기라 대응이 훨씬 멀고,
`game_engine` 은 `upperarm_l` 식이라 좌우 표기까지 다르다.

사슬 정렬 — cmu_mb 는 목이 한 마디 더 길다.

    cmu_mb   Spine -> Spine1 -> Neck  -> Neck1 -> Head
    Mixamo   Spine -> Spine1 -> Spine2 -> Neck  -> Head

그래서 cmu_mb 의 `Neck` 이 Mixamo 의 `Spine2` 자리에, `Neck1` 이 `Neck` 자리에
온다. 마디 수가 같으므로 관절을 새로 만들지 않고 이름만 옮긴다.

끝점 세 개는 cmu_mb 에 없어 **합성한다**. Mixamo 의 `_End` 뼈는 스킨 가중치를
갖지 않는 순수 기하 표식이므로, 같은 정의(해당 부위 메쉬의 끝점)로 만든다.

    mixamorig:HeadTop_End    머리에 묶인 정점의 최상단   <- 키(stature) 계측이 쓴다
    mixamorig:LeftToe_End    발가락 정점의 최전단
    mixamorig:RightToe_End   같음

사용
  blender -b --factory-startup -P tools/makehuman_dae_to_gltf.py -- \
      --dae in.dae --out out.gltf [--tris 26756]

`--tris` 를 주면 삼각형 수를 그 값에 맞춰 감면한다(스킨 가중치는 Blender 의
Decimate 가 함께 옮긴다). 주지 않으면 삼각화만 하고 감면하지 않는다.
"""
import argparse
import os
import sys

import bpy
import mathutils

# cmu_mb -> Mixamo. 값이 None 이면 그 뼈는 쓰지 않는다(이름만 두고 넘어간다).
BONE_MAP = {
    'Hips': 'Hips',
    'Spine': 'Spine',
    'Spine1': 'Spine1',
    'Neck': 'Spine2',        # 사슬 정렬 — 위 설명 참고
    'Neck1': 'Neck',
    'Head': 'Head',
    'LeftShoulder': 'LeftShoulder',
    'LeftArm': 'LeftArm',
    'LeftForeArm': 'LeftForeArm',
    'LeftHand': 'LeftHand',
    'RightShoulder': 'RightShoulder',
    'RightArm': 'RightArm',
    'RightForeArm': 'RightForeArm',
    'RightHand': 'RightHand',
    'LeftUpLeg': 'LeftUpLeg',
    'LeftLeg': 'LeftLeg',
    'LeftFoot': 'LeftFoot',
    'LeftToeBase': 'LeftToeBase',
    'RightUpLeg': 'RightUpLeg',
    'RightLeg': 'RightLeg',
    'RightFoot': 'RightFoot',
    'RightToeBase': 'RightToeBase',
    # 아래는 Mixamo 25관절에 없다. 이름만 바꿔 두면 분할이 이들을 뼈로 쓰지 않는다.
    'LHipJoint': None, 'RHipJoint': None, 'LowerBack': None,
    'LThumb': None, 'RThumb': None,
    'LeftFingerBase': None, 'RightFingerBase': None,
    'LeftHandFinger1': None, 'RightHandFinger1': None,
}
PREFIX = 'mixamorig:'


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--dae', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tris', type=int, default=0,
                    help='목표 삼각형 수 (0 이면 감면하지 않는다)')
    return ap.parse_args(argv)


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def find_objects():
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
    return arm, mesh


def normalize_transforms(arm, mesh):
    """임포트가 남긴 포즈만 지운다. **오브젝트 변환은 건드리지 않는다.**

    Collada 임포트는 메쉬를 배율 1(좌표가 cm)로, 아마추어를 배율 0.01 로 준다.
    둘 다 transform_apply 하면 아마추어 쪽 0.01 이 뼈 길이에 구워져 뼈만 미터가
    되고 메쉬는 cm 로 남는다. 그러면 뼈 전역 위치가 메쉬 대비 100배 작아져
    관절이 전부 원점 근처에 뭉친다(실제로 관절 12개가 키의 0.78 한 점에 모였다).
    임포터가 맞춰 둔 배율 관계를 그대로 두고, 끝점 뼈는 matrix_world 로 계산한다.

    자세는 지운다. 우리가 쓰는 것은 rest 자세뿐이다.
    """
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.ops.object.mode_set(mode='OBJECT')


def triangulate(mesh):
    bpy.context.view_layer.objects.active = mesh
    m = mesh.modifiers.new('tri', 'TRIANGULATE')
    m.quad_method = 'SHORTEST_DIAGONAL'
    bpy.ops.object.modifier_apply(modifier=m.name)


def decimate(mesh, target_tris):
    n = len(mesh.data.polygons)
    if target_tris <= 0 or target_tris >= n:
        return n
    bpy.context.view_layer.objects.active = mesh
    m = mesh.modifiers.new('dec', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.use_collapse_triangulate = True
    m.ratio = float(target_tris) / float(n)
    bpy.ops.object.modifier_apply(modifier=m.name)
    return len(mesh.data.polygons)


def group_vertex_coords(mesh, group_name):
    """해당 vertex group 에 실제 가중치를 가진 정점의 월드 좌표."""
    g = mesh.vertex_groups.get(group_name)
    if g is None:
        return []
    idx = g.index
    mw = mesh.matrix_world
    out = []
    for v in mesh.data.vertices:
        for ge in v.groups:
            # 지배 가중치만 본다. 옅게 섞인 정점까지 넣으면 끝점이 부위 밖으로
            # 끌려간다(발가락 끝이 발 길이의 몇 배로 잡히는 것을 이렇게 잡았다).
            if ge.group == idx and ge.weight > 0.5:
                out.append(mw @ v.co)
                break
    return out


def up_axis(mesh):
    """사람 형상은 가장 긴 축이 곧 세로축이다."""
    ext = [max(v[i] for v in mesh.bound_box) - min(v[i] for v in mesh.bound_box)
           for i in range(3)]
    return ext.index(max(ext))


def add_tip_bones(arm, mesh):
    """Mixamo 의 _End 뼈를 같은 정의(부위 메쉬의 끝점)로 만든다."""
    tips = []
    up = up_axis(mesh)

    head_v = group_vertex_coords(mesh, PREFIX + 'Head')
    if head_v:
        top = max(head_v, key=lambda c: c[up])
        tips.append((PREFIX + 'HeadTop_End', PREFIX + 'Head', top))

    for side in ('Left', 'Right'):
        toe = PREFIX + side + 'ToeBase'
        toe_v = group_vertex_coords(mesh, toe)
        if not toe_v:
            continue
        base = arm.matrix_world @ arm.data.bones[toe].head_local
        far = max(toe_v, key=lambda c: (c - base).length)
        tips.append((PREFIX + side + 'Toe_End', toe, far))

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    inv = arm.matrix_world.inverted()
    for name, parent_name, world_pos in tips:
        parent = arm.data.edit_bones.get(parent_name)
        if parent is None:
            continue
        eb = arm.data.edit_bones.new(name)
        eb.head = inv @ world_pos
        # 길이가 0 이면 Blender 가 뼈를 버린다. 부모 방향으로 짧게 세운다.
        d = (eb.head - parent.head)
        d = d.normalized() if d.length > 1e-6 else mathutils.Vector((0, 0, 1))
        eb.tail = eb.head + d * 0.02
        eb.parent = parent
        eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return [t[0] for t in tips]


def rename_bones(arm, mesh):
    """뼈와 vertex group 을 함께 바꾼다. 둘은 이름으로만 이어져 있다."""
    renamed = {}
    for old, new in BONE_MAP.items():
        b = arm.data.bones.get(old)
        if b is None:
            continue
        target = PREFIX + (new if new else old)
        b.name = target
        renamed[old] = target
    for old, new in renamed.items():
        g = mesh.vertex_groups.get(old)
        if g is not None:
            g.name = new
    return renamed


def add_rest_action(arm):
    """정지 자세 키프레임 하나짜리 액션을 만든다.

    로더(hf_skin_animator)는 애니메이션이 있는 Mixamo 파일만 실전에서 검증돼
    있다. 키프레임 하나를 넣어 두면 우리 파일도 같은 경로를 타므로, 로더의
    정지 자세 분기에 기대지 않아도 된다.
    """
    # 오퍼레이터(bpy.ops.anim.*)는 헤드리스에서 컨텍스트가 없어 실패한다.
    # 데이터 API 로 직접 키를 넣는다.
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.keyframe_insert(data_path='location', frame=0)
        pb.keyframe_insert(data_path='rotation_quaternion', frame=0)
        pb.keyframe_insert(data_path='scale', frame=0)
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = 1


def main():
    a = parse_args()
    clear_scene()
    bpy.ops.wm.collada_import(filepath=a.dae)
    arm, mesh = find_objects()
    normalize_transforms(arm, mesh)

    triangulate(mesh)
    n_tris = decimate(mesh, a.tris)

    renamed = rename_bones(arm, mesh)
    tips = add_tip_bones(arm, mesh)
    add_rest_action(arm)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=a.out,
        export_format='GLTF_SEPARATE',
        export_yup=False,           # Blender 의 Y 세로축을 그대로 = glTF Y-up
        export_skins=True,
        export_animations=True,
        export_frame_range=False,
        export_materials='NONE',
        export_normals=True,
        use_selection=False,
    )
    print('RESULT tris=%d bones=%d renamed=%d tips=%s'
          % (n_tris, len(arm.data.bones), len(renamed), ','.join(tips)))


if __name__ == '__main__':
    main()
