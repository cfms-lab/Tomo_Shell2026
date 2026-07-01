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

		verts = np.empty((1, 3), dtype=float)
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

