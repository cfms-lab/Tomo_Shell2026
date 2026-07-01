import numpy as np
from copy import copy

from cut_colors import cutColorSpan
from cut_object import *
from cut_math import append_bbox
from cut_meshoffset import *

class CutGroup:
	def __init__(self,  name, parent_ps, joints, cutobjects ):
		self.name 			= name
		self.parent_ps	= parent_ps
		self.joints			= joints
		self.cutobjects	= cutobjects
		self.colorspan 	= cutColorSpan()

	def get_shells(self, offset_size):
		o_objects = []
		new_group_name = f"{self.name}_sh"
		for id, c_o in enumerate(self.cutobjects):
			off_tmesh = offset_trimesh( c_o.tmesh, offset_size)
			o_o = CutObject(f"{new_group_name}_{id:02d}", off_tmesh, c_o.color_span, c_o.color_id)
			o_o.tomo_object = c_o.tomo_object.copy()
			o_objects.append(o_o)
		cut_group = CutGroup( new_group_name, self.parent_ps, self.joints, o_objects )
		return cut_group

	def sort_by_color(self):
		from operator import attrgetter
		self.cutobjects = sorted( self.cutobjects, key=lambda x : x.color_id % self.colorspan.n_color)

	def get_bounds(self):
		bmin = np.ones(3) * 1e5
		bmax = np.ones(3) * -1e5
		bbox0 = np.column_stack((bmin,bmax)).T
		for c_o in self.cutobjects:
			if c_o.tmesh:
				bbox0 = append_bbox( bbox0, c_o.tmesh.bounds)
		return bbox0

	def add_to(self, renderer):#show dissected meshes
		child_ps  = renderer.create_group(self.name)
		self.parent_ps.add_child_group(child_ps)
		for c_o in self.cutobjects:
			c_o.add_to( renderer, child_ps, self.colorspan)
		return child_ps

	def layout2D(self, parent_bounds, dirV, dirH):
		if len(self.cutobjects)<=0: return

		dispH = np.multiply( parent_bounds[1] - self.get_bounds()[0], dirH)
		self.translate_by( dispH)

		self.sort_by_color()

		#box packing
		posH = 0
		last_color = 0
		width0 =  np.dot( parent_bounds[1] - parent_bounds[0], dirV)
		for c_o in self.cutobjects:
			if c_o.color_id % self.colorspan.n_color != last_color:
				last_color = c_o.color_id
			sizeV 		= np.dot( c_o.tmesh.bounds[1] - c_o.tmesh.bounds[0], dirV)
			sizeH  		= np.dot( c_o.tmesh.bounds[1] - c_o.tmesh.bounds[0], dirH)
			posV	    = (width0 - sizeV) * 0.5
			c_o.translate_by( dirV * posV + dirH * posH)
			posH     += sizeH

		return self.get_bounds()

	def translate_by(self, vec):#children 전체를 동시에 움직인다.
		for c_o in self.cutobjects:
			c_o.translate_by(vec)
		self.get_bounds()

	def copy(self, prefix=""):
		new_group_name = f"{self.name}{prefix}"
		o_objects = []
		for id, c_o in enumerate(self.cutobjects):
			o_o = CutObject(f"{new_group_name}_{id:02d}", copy(c_o.tmesh), c_o.color_span, c_o.color_id, c_o.tomo_object)
			o_objects.append(o_o)
		return CutGroup( new_group_name, self.parent_ps, self.joints, o_objects)

	def GetMss(self):
		Mss = 0
		obb_lengths = np.empty( (0),dtype=np.float32)
		for c_o in self.cutobjects:
			Mss += c_o.GetMss()
			obb_lengths = np.append( obb_lengths, c_o.tomo_object.best_vminfo.get_max_length())
		len_avg = np.mean( obb_lengths)
		len_std = np.std( obb_lengths)

		print(self.name,"\n",len(obb_lengths), "\n", len_avg, "\n", len_std, "\n", Mss)
