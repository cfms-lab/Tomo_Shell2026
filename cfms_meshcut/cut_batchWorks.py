import os
import numpy as np
from copy import copy, deepcopy
import polyscope as ps #3D renderer by Nicholas Sharp. https://polyscope.run/py/

from highfestiva_gltfLoader import gltfLoader #modified from https://github.com/highfestiva/gltf-skin-anim-viewer
from cfms_meshcut import CutManager
from cfms_meshcut.cut_function import cutType, CutOption
from cfms_tomo import TomoManager
from cfms_tomo.tomo_slicingOptions import SlicingOptions
from cfms_tomo.tomo_io import StartTimer, EndTimer
from cfms_meshcut.cut_math import append_bbox
from cfms_meshcut.cut_group import CutGroup
from cfms_meshcut.cut_laplacian import subdivide_acute_triangle

class Work:
	def __init__(self, avatar, cut_option, slicing_option):
		# (1). mesh clustering
		self.cut_groups : list[CutGroup] = []
		self.avatar 		= avatar #pointer to raw data
		self.cut_option = copy(cut_option)
		self.cutter 		= CutManager(avatar)
		self.cuts					= self.cutter.cut_mesh( cut_option)

		# (2). find optimal orientation of non-closed triangular meshes
		self.tomo 			= TomoManager(  slicing_option)
		self.tomo.get_best_orientation( self.cuts)

		# (3). convert solid mesh into shallow shells
		render_shell_thickness = getattr(
			slicing_option,
			"RenderShellThickness",
			slicing_option.ShellThickness,
		)
		(self.shells, self.bests) = self.tomo.get_shells(render_shell_thickness)

	def layout2D(self, parent_bounds, dirV, dirH):
		# (4). lay out on the xy plane
		dispV = np.multiply( parent_bounds[1] - self.get_bounds()[0], dirV)
		self.translate_by( dispV)
		self.bests.layout2D(  self.cuts.get_bounds(), dirV, dirH)
		return self.get_bounds()

	def add_to(self, renderer):
		# (5). 3D rendering
		self.cuts.add_to(renderer)
		self.shells.add_to(renderer)
		self.bests.add_to(renderer)

	def get_bounds(self):
		self.bounds 	= np.array( [np.zeros(3), np.zeros(3)]) # for layout2D()
		self.bounds 	= append_bbox( self.bounds, self.cuts.get_bounds())
		self.bounds 	= append_bbox( self.bounds, self.shells.get_bounds())
		self.bounds 	= append_bbox( self.bounds, self.bests.get_bounds())
		return self.bounds

	def translate_by(self, vec):
		self.cuts.translate_by(vec)
		self.shells.translate_by(vec)
		self.bests.translate_by(vec)

	def save(self, file_type):
		save_dir 		= self.avatar.basedir + '\\' + self.cut_option.name + '\\'
		os.makedirs( save_dir, exist_ok=True)
		for c_o in self.bests.cutobjects:
			c_o.save(save_dir, file_type)

	def GetMss(self):
		self.bests.GetMss()

class Batch:
	def __init__(self, avatar, cut_options, slicing_option):
		self.avatar = avatar
		self.works = []
		for c_o in cut_options:
			time0 = StartTimer(f"Starting batch: {c_o.name} \n")
			new_work = Work(avatar, c_o, slicing_option)
			self.works.append( new_work)
			EndTimer(time0, f"Ending batch: {c_o.name} \n")
		self.layout2D()

	def layout2D(self):
		self.bounds = np.array( [np.zeros(3), np.zeros(3)])
		dirV = np.array([0.,1.,0.])#C_G 방향 / 색깔별 세로 방향
		dirH = np.array([1.,0.,0.])#색깔별 가로 방향.
		last_bounds = self.avatar.tmesh.bounds
		for w in self.works:
			last_bounds = w.layout2D( last_bounds, dirV, dirH)

	def add_to(self, renderer):
		for w in self.works:
			w.add_to(renderer)

	def save_obj(self):
		for w in self.works:
			w.save(file_type = "obj")

	def GetMss(self):
		print("name n_segment length_average length_stdev Mss \n")
		for w in self.works:
			w.GetMss()
