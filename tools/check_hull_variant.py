#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""볼록껍질 씨앗 한 줄(np.empty)이 계측 정확도에 어떤 영향을 주는지 잰다.

`highfestiva_gltfLoader.gltfLoader.initial_transform` 은 껍질을 만들 때
`verts = np.empty((1, 3))` 로 시작한다. np.empty 는 값을 채우지 않으므로 그 자리에
남아 있던 메모리 값 하나가 점으로 함께 들어간다. 그 점이 껍질의 z 범위를 늘리면
`gltf_rotater.get_matrix()` 의 z_scale 이 작아져 메쉬 전체가 작게 놓인다.

여기서 답하려는 것은 하나다 — **그 줄을 고치면 계측이 좋아지는가 나빠지는가.**
판정 기준은 실행 전에 고정한다: SizeKorea 수기 계측치 대비 **절대 오차율의 평균**이
작은 쪽이 낫다. 항목별로 부호가 갈릴 수 있으므로 평균만 보지 않고 항목별 표도 남긴다.

파일을 고치지 않고 자식 프로세스에서 `initial_transform` 만 갈아 끼운다. 그래야
같은 실행에서 두 변형을 나란히 재도 발표본 코드가 그대로 남는다.

재현성도 함께 본다. np.empty 의 값은 보장되지 않으므로 같은 조건을 여러 번 돌려
값이 흔들리는지 확인한다.

출력: draft_sh4/hull_variant.csv
실행: uv run python tools/check_hull_variant.py
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = os.path.join(ROOT, 'draft_sh4')

MESHES = [  # make_tables.py 의 MESHES 와 같은 목록
    ('F20_4k',  'MeshData/SK6th_F20_4k_NoFinger.gltf',  165.001),
    ('F20_10k', 'MeshData/SK6th_F20_10k_NoFinger.gltf', 165.001),
    ('M20_4k',  'MeshData/SK6th_M20_4k_NoFinger.gltf',  175.99),
    ('M20_87k', 'MeshData/SK6th_M20_87k_NoFinger.gltf', 175.99),
]
ITEMS = ['stature', 'axilla', 'fingertip', 'crotchH', 'neck', 'armscye', 'bust',
         'waist', 'hip', 'thigh', 'calf', 'shoulderW', 'armL', 'waist2mal',
         'crotchTot']

CHILD = r'''
import sys, os, json
import numpy as np
sys.path.insert(0, r"{root}")
sys.path.insert(0, os.path.join(r"{root}", "draft_sh4"))
os.chdir(r"{root}")

variant = "{variant}"
if variant == "fixed":
    # 발표본 파일을 건드리지 않고 이 프로세스에서만 씨앗 한 줄을 뺀다.
    import highfestiva_gltfLoader as G
    def initial_transform(self):
        from gltf_rotater import gltfHull, gltfRotater
        Ani = self.manager.animator
        verts = np.empty((0, 3), dtype=float)     # <- 차이는 이 한 줄뿐
        if Ani.skinned_primitives:
            for p in Ani.skinned_primitives:
                verts = np.append(verts, p.vertices, axis=0)
        else:
            for m in self.manager.model.meshes:
                for p in m.primitives:
                    verts = np.append(verts, p.vertices, axis=0)
        chull = gltfHull(verts)
        mat4x4 = gltfRotater(chull).get_matrix(G.RxRyRz, max_height=self.max_height)
        if Ani.skinned_primitives:
            for model in Ani.skinned_primitives:
                model.initial_transform(mat4x4)
        else:
            self.manager.model.initial_transform(mat4x4)
        Ani.initial_transform(mat4x4)
    G.gltfLoader.initial_transform = initial_transform

import make_tables
out = make_tables.measure_one("{gltf}", {height}, "{method}")
print("JSON," + json.dumps(out))
'''


def run(variant, gltf, height, method):
    code = CHILD.format(root=ROOT, variant=variant, gltf=gltf,
                        height=height, method=method)
    r = subprocess.run([sys.executable, '-c', code],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('JSON,'):
            return json.loads(line[5:])
    raise RuntimeError('failed %s %s\n%s' % (variant, gltf,
                                             r.stdout[-800:] + r.stderr[-800:]))


def load_ref():
    import ast
    src = open(os.path.join(DRAFT, 'make_tables.py'), encoding='utf-8').read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'REF':
            return ast.literal_eval(node.value)
    raise RuntimeError('REF not found')


def main():
    ref = load_ref()
    rows = []
    for tag, gltf, height in MESHES:
        sex = 'F' if tag.startswith('F') else 'M'
        for variant in ('published', 'fixed'):
            d = run(variant, gltf, height, 'p2b')
            errs = []
            for it in ITEMS:
                r = ref[sex][it]
                e = (r - d[it]) / r * 100.0
                errs.append(abs(e))
                rows.append((tag, variant, it, r, d[it], e))
            print('  %-9s %-10s  평균 |오차| = %5.2f %%  (키 %.2f)'
                  % (tag, variant, sum(errs) / len(errs), d['stature']))

    # 재현성: 같은 조건을 세 번
    print('재현성 (published, M20_4k, 3회):')
    seen = []
    for i in range(3):
        d = run('published', 'MeshData/SK6th_M20_4k_NoFinger.gltf', 175.99, 'p2b')
        seen.append(round(d['hip'], 4))
        print('    hip = %.4f' % d['hip'])
    print('    동일한가: %s' % (len(set(seen)) == 1))

    out = os.path.join(DRAFT, 'hull_variant.csv')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('mesh,variant,item,sizekorea,measured,error_pct\n')
        for r in rows:
            f.write('%s,%s,%s,%.2f,%.4f,%.2f\n' % r)
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
