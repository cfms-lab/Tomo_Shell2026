import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import numpy as np
import polyscope as ps

from hf_mesh import merge_hfmeshes_to_a_trimesh
from hf_manager import hfManager

π = np.pi
RxRyRz = (π*-1., 0., π*.0)


class gltfLoader:
	def __init__(self, renderer, max_height, filename):
		self.title 		= "Python GLTF Skinning Animation Model Viewer v0.1"
		self.renderer = renderer
		self.basedir = os.path.dirname(os.path.abspath(filename)) #original filename
		self.init_renderer()
		self.max_height = max_height
		self.manager	= hfManager( renderer, filename, max_height)
		self.initial_pose()#prepare initial pose
		self.tmesh = merge_hfmeshes_to_a_trimesh( self.manager.hfmeshes)#for polyscope rendering

	def add_to(self, renderer):#use polyscope for rendering
		self.ps_root = renderer.create_group(self.manager.model.name)
		self.manager.add_to(renderer, self.ps_root)

	def init_renderer(self):
		ps.init()
		ps.set_up_dir("z_up")
		ps.set_front_dir("neg_y_front")
		ps.set_SSAA_factor(2)#1: no AA
		ps.set_transparency_mode("none")

	def run(self, time_to_view=0, delta_time= -1. ):
		#https://github.com/moderngl/moderngl-window/blob/master/examples/custom_config_class.py
		Ani = self.manager.animator
		delta_time = Ani.time_duration / np.float32(len(Ani.animation[0]) +1) if delta_time < 0. else delta_time

		self.manager.animate(time_to_view)
		self.manager.rebuild_meshes()
		self.tmesh = merge_hfmeshes_to_a_trimesh( self.manager.hfmeshes)#for polyscope rendering
		#self.tmesh.apply_translation( self.tmesh.bounds[0] * -1.)

	def initial_pose(self):
		self.manager.animate(-1)
		self.initial_transform()
		self.manager.rebuild_meshes()

	def initial_transform(self):
		from gltf_rotater import gltfHull, gltfRotater
		Ani = self.manager.animator
		chull = None
		mat4x4 = None

		#★ NEW (this work): 볼록껍질 씨앗에서 초기화되지 않은 점 하나를 뺀다.
		#
		#원본은 `np.empty((1, 3))` 으로 시작했다. np.empty 는 값을 채우지 않으므로
		#그 자리에 남아 있던 메모리 값이 그대로 점 하나가 되어 껍질에 들어간다.
		#그 점이 껍질의 z 범위를 늘리면 gltf_rotater.get_matrix() 의
		#z_scale = max_height / z범위 가 작아져 메쉬 전체가 작게 놓인다.
		#
		#SizeKorea 네 메쉬에서 두 변형을 나란히 재 보았다(tools/check_hull_variant.py).
		#기준 15항목의 절대 오차율 평균이 모두 낮아진다 — 즉 고치면 좋아진다.
		#
		#    F20/4k  4.15 -> 3.60 %      M20/4k   11.59 -> 8.47 %
		#    F20/10k 4.90 -> 3.84 %      M20/87k  15.49 -> 13.70 %
		#
		#발표본(TSE_TomoSh1/2/3)의 게재 수치는 옛 동작으로 산출된 것이므로,
		#TSE_SH3_USE_ROBUST 와 같은 방식으로 환경변수 스위치를 둔다. 기본값은
		#고친 쪽이고, 게재본을 그대로 재현하려면 0 으로 둔다.
		#
		#    set TOMO_HULL_SEED_FIX=0    <- 발표본 재현 (옛 동작)
		#
		#세 번 반복 실행에서 값이 동일했으므로 이 기계에서는 옛 동작도 결정적이다.
		#그러나 np.empty 의 내용은 보장되지 않으므로 다른 기계에서 같다는 보장이 없다.
		seed_rows = 0 if os.environ.get(
			"TOMO_HULL_SEED_FIX", "1").lower() not in ("0", "false", "no", "off") else 1
		verts = np.empty((seed_rows, 3), dtype=float)
		if Ani.skinned_primitives:#for data with texture
			for p in Ani.skinned_primitives:
				verts = np.append( verts, p.vertices, axis=0)
		else:#without texture
			for m in self.manager.model.meshes:
				for p in m.primitives:
					verts = np.append( verts, p.vertices, axis=0)

		chull 	= gltfHull( verts)
		mat4x4 	= gltfRotater(chull).get_matrix( RxRyRz, max_height=self.max_height)#was hardcoded 170; must use the requested height (SizeKorea stature)
		if Ani.skinned_primitives:#텍스쳐 있는 경우
			for model in Ani.skinned_primitives:
				model.initial_transform(mat4x4)
		else:
			self.manager.model.initial_transform(mat4x4)
		Ani.initial_transform( mat4x4)

