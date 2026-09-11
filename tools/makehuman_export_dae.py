#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MakeHuman 합성 인체를 리그 포함 Collada 로 내보낸다 (GUI 없이).

볼트 노트 [[MakeHuman 설치와 사용 주의사항 2026-09-08]] 는 생성 스크립트를
Scripting 탭에서 돌리라고 적는다. 그러나 GUI 없이도 된다 — 앱 전역 `G.app` 만
최소 스텁으로 채우면 core 모듈이 그대로 import 되고 `applyAllTargets()`,
`setSkeleton()`, 번들 Collada 내보내기까지 전부 동작한다. 2026-09-10 확인.

GUI 를 띄우지 않으므로 Scripting 탭의 제약(`def`·컴프리헨션 금지)도 없다.

리그는 **cmu_mb** 를 쓴다. 번들 리그 넷 중 뼈 이름이 Mixamo 와 사실상 같아
계측 파이프라인의 `mixamorig:*` 조회에 가장 가깝다. 이름을 옮기고 끝점 뼈를
더하는 것은 `tools/makehuman_dae_to_gltf.py` 가 맡는다.

라이선스: 번들 자산 + 번들 내보내기만 쓴다. 에셋 저장소에서 내려받지 않는다.
동봉 `LICENSE.md` §D 가 스크립팅 출력도 covered 로 명시한다.
자세한 것은 볼트 [[MakeHuman 라이선스 정리 2026-09-08]].

사용
  "C:/Program Files/makehuman-community/Python/python.exe" \
      tools/makehuman_export_dae.py --mhm body.mhm --out body.dae
  ... --gender 1.0 --height 0.5 --weight 0.75 --out body.dae
"""
import argparse
import os
import sys

MH_ROOT = r"C:\Program Files\makehuman-community\makehuman"


def bootstrap():
    for sub in ("", "lib", "apps", "shared", "core", "plugins"):
        p = os.path.join(MH_ROOT, sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(MH_ROOT)


class StubApp(object):
    """MakeHuman 이 전역으로 기대하는 앱 객체의 최소 대역.

    progress()/status() 는 진행 표시용이라 비워 두면 되고, getSetting() 은
    실제 기본값과 같은 값을 돌려준다. 이것만 있으면 모델링·리깅·내보내기가
    GUI 없이 끝까지 간다.
    """

    selectedHuman = None
    currentTask = None
    # .mhm 을 읽을 때 human.load() 가 앱의 로더 표를 찾는다. 우리는 매크로
    # 슬라이더만 쓰므로 빈 표로 충분하다(의상·헤어 등은 애초에 쓰지 않는다).
    loadHandlers = {}
    saveHandlers = {}
    modelCamera = None   # load() 가 카메라를 되돌리려 할 때만 쓴다

    def progress(self, *a, **k):
        pass

    def status(self, *a, **k):
        pass

    def statusPersist(self, *a, **k):
        pass

    def getSetting(self, name):
        return {'units': 'metric', 'realtimeUpdates': False,
                'realtimeNormalUpdates': False, 'realtimeFitting': False,
                'cameraAutoZoom': False, 'lowspeed': 1,
                'preloadTargets': False, 'sliderImages': False}.get(name)

    def setSetting(self, *a, **k):
        pass

    def refreshStaticMeshes(self, *a, **k):
        pass

    def redraw(self, *a, **k):
        pass

    def callAsync(self, fn, *a, **k):
        return fn()

    def addTask(self, *a, **k):
        pass


def build_human(args):
    import getpath
    import files3d
    import human as human_mod
    import humanmodifier
    import skeleton
    from core import G

    G.app = StubApp()
    mesh = files3d.loadMesh(getpath.getSysDataPath("3dobjs/base.obj"))
    h = human_mod.Human(mesh)
    G.app.selectedHuman = h
    humanmodifier.loadModifiers(
        getpath.getSysDataPath('modifiers/modeling_modifiers.json'), h)

    if args.mhm:
        h.load(args.mhm, update=True)
    else:
        h.getModifier('macrodetails/Gender').setValue(args.gender)
        h.getModifier('macrodetails-height/Height').setValue(args.height)
        h.getModifier('macrodetails-universal/Weight').setValue(args.weight)
    h.applyAllTargets()

    # 기준 리그를 먼저 세워야 가중치가 생기고, 그 뒤에야 cmu_mb 로 재사상된다.
    h.setBaseSkeleton(
        skeleton.load(getpath.getSysDataPath('rigs/default.mhskel'), h.meshData))
    h.setSkeleton(
        skeleton.load(getpath.getSysDataPath('rigs/cmu_mb.mhskel'), h.meshData))
    return h


def export_dae(h, out_path):
    from importlib import import_module
    pkg = import_module('9_export_collada')
    cfg = pkg.DaeConfig()
    cfg.setHuman(h)
    # 앱의 "centimeter" 설정과 같은 값. 기본은 데시미터라 그대로 두면 키가 17 이 된다.
    cfg.scale, cfg.unit = 10.0, "centimeter"
    cfg.feetOnGround = False
    cfg.hiddenGeom = False          # helper 기하를 빼야 단일 성분 몸이 된다
    cfg.facePoseUnits = False
    cfg.yUpFaceZ, cfg.yUpFaceX = True, False
    cfg.zUpFaceNegY, cfg.zUpFaceX = False, False
    cfg.localY, cfg.localX, cfg.localG = True, False, False
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    import_module('9_export_collada.mh2collada').exportCollada(out_path, cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mhm', help='불러올 .mhm (주면 슬라이더 인자는 무시된다)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--gender', type=float, default=0.5)
    ap.add_argument('--height', type=float, default=0.5)
    ap.add_argument('--weight', type=float, default=0.5)
    a = ap.parse_args()

    bootstrap()
    h = build_human(a)
    export_dae(h, a.out)
    print('RESULT height_cm=%.2f out=%s size=%d'
          % (h.getHeightCm(), a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
