#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""makehuman_dae_to_rig.py 가 만든 .npz 를 계측 파이프라인에 물리는 어댑터.

`CutManager` 가 아바타에게 요구하는 것은 좁다.

    avatar.tmesh                              삼각형 메쉬
    avatar.manager.animator.joints            이름이 붙은 뼈 (name/xyz/parent_*)
    avatar.manager.get_end_bone_pos()         분할용 뼈 여섯 쌍
    avatar.manager.get_bone_pos_by_name(n)    이름으로 뼈 위치

이 파일은 그 인터페이스만 흉내 낸다. glTF 로더의 스키닝·역바인드행렬·축 규약을
거치지 않으므로, 그쪽 규약을 되짚을 필요가 없다. 발표본 코드는 건드리지 않는다.

좌표계: npz 는 MakeHuman 그대로 Y 가 세로축이고 원점이 몸 가운데다.
파이프라인은 z 를 키로 읽고 바닥이 0 이라고 본다(`make_screenshots.py` 가
`bounds[2]` 를 높이로 쓴다). 여기서 한 번 세우고 바닥을 0 으로 내린다.
"""
import os
import sys

import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cfms_meshcut import CutManager                       # noqa: E402
from cfms_meshcut.cut_function import cutType, CutOption  # noqa: E402

# gltfLoader 가 쓰는 분할용 뼈 쌍과 같은 목록 (hf_manager.get_end_bone_pos)
P2B_CHILD = ['mixamorig:HeadTop_End', 'mixamorig:LeftForeArm', 'mixamorig:RightForeArm',
             'mixamorig:LeftFoot', 'mixamorig:RightFoot', 'mixamorig:Neck']
P2B_PARENT = ['mixamorig:Head', 'mixamorig:LeftHand', 'mixamorig:RightHand',
              'mixamorig:LeftLeg', 'mixamorig:RightLeg', 'root']


class JointInfo:
    def __init__(self, name, xyz, parent_name, parent_xyz):
        self.name = name
        self.xyz = xyz
        self.parent_name = parent_name
        self.parent_xyz = parent_xyz


class _Animator:
    def __init__(self, joints):
        self.joints = joints
        self.skinned_primitives = None


class _Manager:
    """hfManager 의 대역. 분할이 부르는 두 메서드와 이름만 있으면 된다.

    `filename` 은 계측 쪽(`BodyMeasure`)이 CutObject 이름을 짓는 데 쓴다.
    분할만 할 때는 닿지 않지만 계측까지 태우면 필요하다.
    """

    def __init__(self, joints, root_xyz, filename=''):
        self.animator = _Animator(joints)
        self.model = None
        self._root = root_xyz
        self.filename = filename

    def get_bone_pos_by_name(self, bone_name):
        if bone_name == 'root':
            return self._root
        for j in self.animator.joints:
            if j.name == bone_name:
                return j.xyz
        return None

    def get_unit_vec(self, b0, b1):
        """hfManager 와 같은 규약. 계측이 기준 축을 세울 때 쓴다."""
        v0 = np.array(self.get_bone_pos_by_name(b0), dtype=float)
        v1 = np.array(self.get_bone_pos_by_name(b1), dtype=float)
        d = v1 - v0
        n = float(np.linalg.norm(d))
        return d / n if n > 0 else d

    def get_end_bone_pos(self):
        child, parent = [], []
        for b0, b1 in zip(P2B_CHILD, P2B_PARENT):
            child.append(self.get_bone_pos_by_name(b0))
            parent.append(self.get_bone_pos_by_name(b1))
        return np.array(child), np.array(parent)


class MHAvatar:
    """`gltfLoader` 자리에 그대로 끼워 넣을 수 있는 아바타."""

    def __init__(self, npz_path, max_height=None):
        d = np.load(npz_path, allow_pickle=True)
        V = np.asarray(d['vertices'], dtype=float)
        F = np.asarray(d['faces'], dtype=np.int64)
        heads = np.asarray(d['bone_head'], dtype=float)
        names = [str(n) for n in d['bone_names']]
        parents = np.asarray(d['bone_parent'], dtype=int)
        self.vertex_bone = np.asarray(d['vertex_bone'], dtype=int)
        self.bone_names = names

        up = int(np.argmax(V.max(axis=0) - V.min(axis=0)))
        V, heads = self._to_z_up(V, heads, up)
        if max_height:
            s = float(max_height) / (V[:, 2].max() - V[:, 2].min())
            V *= s
            heads *= s
        shift = np.array([0.0, 0.0, -V[:, 2].min()])
        V += shift
        heads += shift

        self.tmesh = trimesh.Trimesh(vertices=V, faces=F, process=False)
        joints = []
        for i, nm in enumerate(names):
            p = parents[i]
            joints.append(JointInfo(nm, heads[i],
                                    names[p] if p >= 0 else 'root',
                                    heads[p] if p >= 0 else heads[i]))
        hips = names.index('mixamorig:Hips') if 'mixamorig:Hips' in names else 0
        stem = os.path.splitext(os.path.basename(npz_path))[0]
        self.manager = _Manager(joints, heads[hips], filename=stem)
        self.basedir = os.path.dirname(os.path.abspath(npz_path))
        self.max_height = max_height

    @staticmethod
    def _to_z_up(V, heads, up):
        """세로축을 z 로 보낸다. 이미 z 면 그대로 둔다.

        ★ 2026-09-11 정정. 이전에는 축을 자리바꿈([x, z, y])만 했는데, 두 축을 맞바꾸는
        것은 회전이 아니라 **반사**(행렬식 −1)라서 삼각형의 감기는 방향이 뒤집히고
        법선이 모두 몸 안쪽을 향했다(trimesh 부피가 음수). 점-뼈대 거리의 법선 패널티는
        법선 방향으로 뼈대의 안팎을 가르므로, 뒤집힌 법선은 패널티를 반대로 적용한다.
        2026-09-11 이전에 이 어댑터로 산출한 합성 인체 결과는 모두 그 상태였다.
        여기서는 행렬식 +1 인 회전(x 축 둘레 +90°)으로 바꾼다: (x, y, z) → (x, −z, y).
        """
        if up == 2:
            return V, heads

        def rot(P):
            Q = np.empty_like(P)
            if up == 1:            # y 가 세로축: x 축 둘레로 90° 회전
                Q[:, 0] = P[:, 0]; Q[:, 1] = -P[:, 2]; Q[:, 2] = P[:, 1]
            else:                  # x 가 세로축: y 축 둘레로 90° 회전
                Q[:, 0] = -P[:, 2]; Q[:, 1] = P[:, 1]; Q[:, 2] = P[:, 0]
            return Q
        return rot(V), rot(heads)


class MHCutManager(CutManager):
    """스킨 가중치 분할만 npz 의 지배 뼈를 쓰도록 갈아 끼운 CutManager.

    원본 `skinweight_groups()` 는 glTF 의 skin/joints/weights 를 직접 읽는데
    우리는 그 경로를 쓰지 않는다. 부위 대응 규칙(이름 키워드)은 원본과 같다.
    """

    def __init__(self, avatar, **kw):
        super().__init__(avatar, **kw)
        self._vertex_bone = avatar.vertex_bone
        self._bone_names = avatar.bone_names

    @staticmethod
    def part_of(name):
        n = name or ''
        if any(k in n for k in ('Hand', 'Arm', 'Shoulder')):
            return 2 if 'Left' in n else 3
        if any(k in n for k in ('Leg', 'Foot', 'Toe')):
            return 4 if 'Left' in n else 5
        if any(k in n for k in ('Head', 'Neck', 'Eye')):
            return 0
        return 1

    def skinweight_groups(self, V):
        part = np.array([self.part_of(n) for n in self._bone_names], dtype=int)
        lab = np.where(self._vertex_bone >= 0,
                       part[np.clip(self._vertex_bone, 0, len(part) - 1)], 1)
        if len(lab) == len(V):
            return lab
        from scipy.spatial import cKDTree      # 감면된 메쉬면 최근접으로 옮긴다
        src = np.asarray(self.tmesh.vertices)
        _, idx = cKDTree(src).query(np.asarray(V), k=1)
        return lab[np.clip(idx, 0, len(lab) - 1)]


def segment_stats(npz_path, method, max_height=None, tag='seg'):
    """한 메쉬에 한 분할법을 적용하고 개수와 **면적**을 함께 돌려준다.

    개수만 세면 「조각이 몇 개인가」는 알아도 「얼마나 잘못 붙었는가」는 모른다.
    체형이 굵어질수록 조각 수는 그대로인데 잘못 분류된 면적이 커지는 것이
    실제로 관찰되므로, 부위마다 가장 큰 연결성분을 제외한 나머지 면적을 더해
    전체 체표면적으로 나눈 값을 함께 잰다.

    tag 는 polyscope 그룹 이름에 들어간다. 한 프로세스에서 여러 번 부르려면
    매번 달라야 한다 — polyscope 는 같은 이름의 그룹을 두 번 등록하지 못한다.
    """
    av = MHAvatar(npz_path, max_height=max_height)
    mgr = MHCutManager(av)
    cg = mgr.cut_mesh(CutOption(tag, getattr(cutType, method), 6))
    per, bad_area, tot_area = [], 0.0, 0.0
    for c in cg.cutobjects:
        comps = [x for x in c.tmesh.split(only_watertight=False)
                 if len(x.vertices) > 3]
        per.append(len(comps))
        areas = sorted((float(x.area) for x in comps), reverse=True)
        tot_area += sum(areas)
        bad_area += sum(areas[1:])          # 가장 큰 것 외에는 오분류로 본다
    return per, bad_area, tot_area


def segment(npz_path, method, max_height=None, tag='seg'):
    """부위별 연결성분 개수만 필요할 때 쓰는 얇은 껍데기."""
    per, _, _ = segment_stats(npz_path, method, max_height, tag)
    return per


# 군집 번호(뼈 쌍 순서: 머리, 왼팔, 오른팔, 왼다리, 오른다리, 몸통) → part_of() 의 부위 코드
P2B_CLUSTER_TO_PART = np.array([0, 2, 3, 4, 5, 1])


def face_labels_from_cut(tmesh, cg):
    """cut_mesh 가 만든 조각들을 원 메쉬의 면 라벨로 되돌린다.

    cut_mesh 는 정점 라벨을 남기지 않고 부분 메쉬만 돌려주므로, 조각의 삼각형
    무게중심을 원 메쉬의 삼각형 무게중심에 맞춰(최근접) 어느 군집(f_s_id, 이름의
    `sub%02d`)에서 왔는지 복원한다. 빈 군집이 있어도 이름의 번호를 쓰므로 어긋나지 않는다.
    """
    import re
    from scipy.spatial import cKDTree
    FC = np.asarray(tmesh.triangles_center)
    tree = cKDTree(FC)
    lab = -np.ones(len(FC), dtype=int)
    for c in cg.cutobjects:
        m = re.search(r'_sub(\d\d)\d\d$', c.name)
        gid = int(m.group(1)) if m else -1
        _, idx = tree.query(np.asarray(c.tmesh.triangles_center), k=1)
        lab[idx] = gid
    return lab


def skinweight_face_labels(mgr, tmesh):
    """스킨 가중치(지배 뼈)에서 얻은 면 라벨. cut_mesh 와 같은 다수결 규칙으로 면에 올린다."""
    vlab = np.asarray(mgr.skinweight_groups(np.asarray(tmesh.vertices)), dtype=int)
    g = vlab[np.asarray(tmesh.faces)]
    return np.where(g[:, 0] == g[:, 1], g[:, 0], np.where(g[:, 1] == g[:, 2], g[:, 1], g[:, 2]))


def segment_stats2(npz_path, method, max_height=None, tag='seg'):
    """segment_stats + 스킨 가중치 라벨과의 **면적 일치율**(%).

    연결성분 개수와 주 성분 밖 면적은 「조각이 몇 개로 쪼개졌나·얼마나 넓나」만 재고,
    한 부위의 표면이 통째로 이웃 부위의 본체에 붙어 버린 오분류는 놓친다(그 표면은
    이웃 부위의 가장 큰 조각에 속하므로 「주 성분 밖」이 아니다). 합성 인체에는 리깅이
    붙인 스킨 가중치가 있으므로 그것을 참조 라벨로 삼아, 각 삼각형의 분할 라벨이 참조와
    같은 면적의 비율을 함께 잰다. 스킨 가중치 분할 자체는 정의상 100 % 다.
    2026-09-11 피어리뷰(P1-m12: 정답 라벨 없음)에 답하려고 추가했다.
    """
    av = MHAvatar(npz_path, max_height=max_height)
    mgr = MHCutManager(av)
    cg = mgr.cut_mesh(CutOption(tag, getattr(cutType, method), 6))
    per, bad_area, tot_area = [], 0.0, 0.0
    for c in cg.cutobjects:
        comps = [x for x in c.tmesh.split(only_watertight=False)
                 if len(x.vertices) > 3]
        per.append(len(comps))
        areas = sorted((float(x.area) for x in comps), reverse=True)
        tot_area += sum(areas)
        bad_area += sum(areas[1:])
    lab = face_labels_from_cut(av.tmesh, cg)
    if method != 'bone_skinweight':
        lab = np.where(lab >= 0, P2B_CLUSTER_TO_PART[np.clip(lab, 0, 5)], -1)
    ref = skinweight_face_labels(mgr, av.tmesh)
    fa = np.asarray(av.tmesh.area_faces)
    agree = 100.0 * float(fa[lab == ref].sum() / fa.sum())
    return per, bad_area, tot_area, agree
