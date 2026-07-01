import os
from copy import copy, deepcopy

import numpy as np
import polyscope as ps #3D renderer by Nicholas Sharp. https://polyscope.run/py/

#from highfestiva_gltfLoader import gltfLoader #modified from https://github.com/highfestiva/gltf-skin-anim-viewer
from cfms_meshcut import CutManager
from cfms_meshcut.cut_math import append_bbox
from cfms_meshcut.cut_group import CutGroup
from cfms_bodym import BodyMeasure


class Work:
	def __init__(self, avatar, cut_option, slicing_option):
		# (1). mesh clustering
		self.avatar 		= avatar #pointer to raw data
		self.cut_option = copy(cut_option)
		self.cutter 		= CutManager(avatar)
		self.cut_group	= self.cutter.cut_mesh( cut_option)
		self.bodym			= BodyMeasure( avatar, self.cut_group)#BodyPart 구분을 위한 임시 객체

	def layout2D(self, parent_bounds, dirV, dirH):# lay out on the xy plane
		dispV = np.multiply( parent_bounds[1] - self.get_bounds()[0], dirV)
		self.translate_by( dispV)
		return self.get_bounds()

	def add_to(self, renderer):
		self.cut_group.add_to(renderer)

	def get_bounds(self):
		self.bounds 	= np.array( [np.zeros(3), np.zeros(3)]) # for layout2D()
		self.bounds 	= append_bbox( self.bounds, self.cut_group.get_bounds())
		return self.bounds

	def translate_by(self, vec):
		self.cut_group.translate_by(vec)

	def save(self, file_type):
		save_dir 		= self.avatar.basedir + '\\' + self.cut_option.name + '\\'
		os.makedirs( save_dir, exist_ok=True)
		#for c_o in self.bests.cutobjects:
		#	c_o.save(save_dir, file_type)

	def getBP(self, bp_name):# 이름이 bp_name인 cutobject를 반환한다.
		for c_o in self.cut_group.cutobjects:
			if c_o.BodyPartID == bp_name:
				return c_o
		return None

class WorkManager:
	def __init__(self, avatar, cut_options, slicing_option = None):

		self.avatar = avatar
		self.works = []
		for cut_option in cut_options:
			new_work = Work(avatar, cut_option, slicing_option)
			self.works.append( new_work)

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

	def getBodyParts(self, part_list : list):
		cutobjects = []
		for (cut_name, bp_id0, bp_id1) in part_list:
			for work in self.works:
				if work.cut_option[0] == cut_name:
					c_o = work.getBP( bp_id0)
					if c_o:
						c_o_2 = copy(c_o)
						c_o_2.name += f'(from_{cut_name})'
						if bp_id1:
							c_o_2.BodyPartID = bp_id1
						cutobjects.append( c_o_2)
						break
		new_name = "BodyM"
		new_ps_id = ps.create_group( f"{new_name}_G")
		return CutGroup( new_name, new_ps_id, self.works[0].avatar.manager.animator.joints, cutobjects )

