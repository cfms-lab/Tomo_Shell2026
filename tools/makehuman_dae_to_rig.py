"""MakeHuman Collada -> 계측 파이프라인용 리그 번들 (Blender 헤드리스)

glTF 를 거치지 않는다. 파이프라인이 `gltfLoader` 에서 실제로 쓰는 것은 두 가지뿐이다.

  * `avatar.tmesh`                      삼각형 메쉬
  * `manager.animator.joints`           이름이 붙은 뼈 위치
    (그 위에서 `get_end_bone_pos()` 와 `get_bone_pos_by_name()` 이 돈다)

glTF 경로는 스키닝·역바인드행렬·축 규약·쿼터니언 성분 순서가 모두 얽혀 있어
MakeHuman 산 파일에서 뼈 위치가 어긋났다. 필요한 것은 정지 자세의 뼈 좌표뿐이므로
Blender 에서 그 값을 직접 뽑아 `.npz` 로 넘긴다. 스키닝을 다시 계산할 이유가 없다.

내보내는 것

  vertices      (N,3) float32   월드 좌표, cm
  faces         (M,3) int32     삼각형
  bone_names    (B,)  str       Mixamo 표기
  bone_head     (B,3) float32   각 뼈의 시작점(월드, cm)
  bone_tail     (B,3) float32   끝점
  bone_parent   (B,)  int32     부모 인덱스, 뿌리는 -1
  vertex_bone   (N,)  int32     지배 뼈 인덱스 (스킨 가중치 분할용)

사용
  blender -b --factory-startup -P tools/makehuman_dae_to_rig.py -- \
      --dae in.dae --out out.npz [--tris 26756]
"""
import argparse
import os
import sys

import bpy
import mathutils
import numpy as np

# cmu_mb -> Mixamo. cmu_mb 는 목이 한 마디 더 길어 Neck 이 Spine2 자리에 온다.
#     cmu_mb   Spine -> Spine1 -> Neck   -> Neck1 -> Head
#     Mixamo   Spine -> Spine1 -> Spine2 -> Neck   -> Head
BONE_MAP = {
    'Hips': 'Hips', 'Spine': 'Spine', 'Spine1': 'Spine1',
    'Neck': 'Spine2', 'Neck1': 'Neck', 'Head': 'Head',
    'LeftShoulder': 'LeftShoulder', 'LeftArm': 'LeftArm',
    'LeftForeArm': 'LeftForeArm', 'LeftHand': 'LeftHand',
    'RightShoulder': 'RightShoulder', 'RightArm': 'RightArm',
    'RightForeArm': 'RightForeArm', 'RightHand': 'RightHand',
    'LeftUpLeg': 'LeftUpLeg', 'LeftLeg': 'LeftLeg',
    'LeftFoot': 'LeftFoot', 'LeftToeBase': 'LeftToeBase',
    'RightUpLeg': 'RightUpLeg', 'RightLeg': 'RightLeg',
    'RightFoot': 'RightFoot', 'RightToeBase': 'RightToeBase',
}
PREFIX = 'mixamorig:'


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--dae', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tris', type=int, default=0, help='감면 목표 삼각형 수')
    ap.add_argument('--subdiv', type=int, default=0, help='단순 세분 단계 (형상 보존, 단계당 6배)')
    return ap.parse_args(argv)


def prepare(dae):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.wm.collada_import(filepath=dae)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
    # 자세만 지운다. 오브젝트 변환은 건드리지 않는다 — 메쉬(배율 1, cm)와
    # 아마추어(배율 0.01)의 관계를 임포터가 맞춰 두었고, 여기서 apply 하면
    # 아마추어 쪽 배율만 뼈 길이에 구워져 뼈가 미터가 된다.
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm, mesh


def resample(mesh, target_tris, subdiv):
    """삼각형 밀도를 바꾼다. 두 방향의 성격이 다르므로 섞지 않는다.

    subdiv > 0 : **단순 세분만** 한다. Catmull-Clark 과 달리 정점을 움직이지
        않으므로 표면이 원본과 완전히 같고 삼각형만 늘어난다. 삼각형 하나가
        쿼드 3개가 되고 다시 삼각화되어 한 단계에 정확히 6배가 된다.
        「형상은 그대로 두고 밀도만 올렸을 때」를 재는 유일한 방법이다.

    target_tris > 0 : Decimate(COLLAPSE) 로 내린다. 이쪽은 형상도 함께 바뀌며,
        SizeKorea 의 4k/10k 등급이 만들어진 방식과 같다.

    둘을 함께 주지 않는다. 세분한 뒤 목표치로 내리면 결국 감면이 되어
    「형상 고정」이라는 성질이 사라진다.
    """
    bpy.context.view_layer.objects.active = mesh
    m = mesh.modifiers.new('tri', 'TRIANGULATE')
    m.quad_method = 'SHORTEST_DIAGONAL'
    bpy.ops.object.modifier_apply(modifier=m.name)
    native = len(mesh.data.polygons)

    if subdiv > 0:
        for _ in range(subdiv):
            sub = mesh.modifiers.new('sub', 'SUBSURF')
            sub.subdivision_type = 'SIMPLE'
            sub.levels = sub.render_levels = 1
            bpy.ops.object.modifier_apply(modifier=sub.name)
            tri = mesh.modifiers.new('tri2', 'TRIANGULATE')
            tri.quad_method = 'SHORTEST_DIAGONAL'
            bpy.ops.object.modifier_apply(modifier=tri.name)
        return len(mesh.data.polygons), native, 'subdivide'

    if 0 < target_tris < native:
        d = mesh.modifiers.new('dec', 'DECIMATE')
        d.decimate_type = 'COLLAPSE'
        d.use_collapse_triangulate = True
        d.ratio = float(target_tris) / float(native)
        bpy.ops.object.modifier_apply(modifier=d.name)
        return len(mesh.data.polygons), native, 'decimate'

    return native, native, 'native'


def up_axis(coords):
    ext = coords.max(axis=0) - coords.min(axis=0)
    return int(np.argmax(ext))


def collect(arm, mesh):
    mw_m = mesh.matrix_world
    verts = np.array([list(mw_m @ v.co) for v in mesh.data.vertices], dtype=np.float32)
    faces = np.array([list(p.vertices) for p in mesh.data.polygons], dtype=np.int32)

    # 지배 뼈: 가중치가 가장 큰 vertex group
    gname = {g.index: g.name for g in mesh.vertex_groups}
    dom = np.full(len(mesh.data.vertices), -1, dtype=np.int32)
    dom_name = [''] * len(mesh.data.vertices)
    for i, v in enumerate(mesh.data.vertices):
        best_w, best_g = 0.0, None
        for ge in v.groups:
            if ge.weight > best_w:
                best_w, best_g = ge.weight, ge.group
        if best_g is not None:
            dom_name[i] = gname.get(best_g, '')

    mw_a = arm.matrix_world
    names, heads, tails, parents = [], [], [], []
    index_of = {}
    for b in arm.data.bones:
        new = BONE_MAP.get(b.name)
        if new is None:
            continue                      # Mixamo 25관절에 없는 뼈는 싣지 않는다
        index_of[b.name] = len(names)
        names.append(PREFIX + new)
        heads.append(list(mw_a @ b.head_local))
        tails.append(list(mw_a @ b.tail_local))
    for b in arm.data.bones:
        if b.name not in index_of:
            continue
        p = b.parent
        while p is not None and p.name not in index_of:
            p = p.parent                  # 중간의 LHipJoint/LowerBack 등을 건너뛴다
        parents.append(index_of[p.name] if p is not None else -1)

    heads = np.array(heads, dtype=np.float32)
    tails = np.array(tails, dtype=np.float32)

    # 끝점 뼈 — Mixamo 의 _End 는 스킨 가중치 없는 기하 표식이다. 같은 정의로 만든다.
    up = up_axis(verts)
    extra_n, extra_h, extra_t, extra_p = [], [], [], []

    cmu_of = {v: k for k, v in BONE_MAP.items()}   # Mixamo -> cmu_mb

    def dom_verts(mixamo_short):
        """해당 부위에 지배적으로 묶인 정점. vertex group 이름은 cmu_mb 표기다."""
        want = cmu_of.get(mixamo_short)
        idx = [i for i, nm in enumerate(dom_name) if nm == want]
        return verts[idx] if idx else None

    hv = dom_verts('Head')
    if hv is not None and PREFIX + 'Head' in names:
        top = hv[np.argmax(hv[:, up])]
        extra_n.append(PREFIX + 'HeadTop_End')
        extra_h.append(top); extra_t.append(top)
        extra_p.append(names.index(PREFIX + 'Head'))
    for side in ('Left', 'Right'):
        toe = PREFIX + side + 'ToeBase'
        tv = dom_verts(side + 'ToeBase')
        if tv is None or toe not in names:
            continue
        base = heads[names.index(toe)]
        far = tv[np.argmax(np.linalg.norm(tv - base, axis=1))]
        extra_n.append(PREFIX + side + 'Toe_End')
        extra_h.append(far); extra_t.append(far)
        extra_p.append(names.index(toe))

    if extra_n:
        names += extra_n
        heads = np.vstack([heads, np.array(extra_h, dtype=np.float32)])
        tails = np.vstack([tails, np.array(extra_t, dtype=np.float32)])
        parents += extra_p

    # 손가락·LHipJoint 처럼 25관절에 없는 뼈에 묶인 정점은 버리지 않고
    # 가장 가까운 조상 부위로 올린다. 버리면 손·골반 표면이 통째로 빠진다.
    bone_by_name = {b.name: b for b in arm.data.bones}

    def resolve(cmu_name):
        b = bone_by_name.get(cmu_name)
        while b is not None and b.name not in BONE_MAP:
            b = b.parent
        return BONE_MAP[b.name] if b is not None else None

    name_to_i = {n: i for i, n in enumerate(names)}
    resolved = {}
    for i, nm in enumerate(dom_name):
        if not nm:
            continue
        if nm not in resolved:
            m = resolve(nm)
            resolved[nm] = name_to_i.get(PREFIX + m, -1) if m else -1
        dom[i] = resolved[nm]

    return dict(vertices=verts, faces=faces,
                bone_names=np.array(names), bone_head=heads, bone_tail=tails,
                bone_parent=np.array(parents, dtype=np.int32), vertex_bone=dom)


def main():
    a = parse_args()
    arm, mesh = prepare(a.dae)
    n_tris, native, how = resample(mesh, a.tris, a.subdiv)
    data = collect(arm, mesh)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez_compressed(a.out, **data)
    ext = data['vertices'].max(axis=0) - data['vertices'].min(axis=0)
    print('RESULT tris=%d native=%d how=%s verts=%d bones=%d extent=%s'
          % (n_tris, native, how, len(data['vertices']), len(data['bone_names']),
             np.round(ext, 2).tolist()))


if __name__ == '__main__':
    main()
