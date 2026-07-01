import numpy as np
from copy import copy

from .tomo_result import TomoResult
from cfms_meshcut.cut_colors import cutColorSpan, TomoPixelColors

class  TomoObject:#find optimal orientation and filament mass needed for FDM 3D printing

	def __init__(self, cutobject, pxl_groups = None, best = None, colorspan = None, mat4x4 = None):#open3D -> trimesh 함수로 변경.
		self.raw_cutobject = cutobject#pointer to raw edata
		self.pxl_groups = []
		if pxl_groups:
			for pxls in pxl_groups:
				self.pxl_groups.append( pxls.copy())
		self.best_vminfo  = copy(best) if best else TomoResult()
		self.colorspan = copy(colorspan) if colorspan else cutColorSpan(TomoPixelColors)
		self.mat4x4			= mat4x4.copy() if mat4x4 is not None else None

	def add_to(self, ps, parent_group_id):
		for p in self.pxl_groups:
			name = f"{self.raw_cutobject.name}_{p.name}"
			p_cloud = ps.register_point_cloud( name, p.pxls, radius=0.001 )#render support structure pixels
			p_cloud.set_color( self.colorspan.get_color_float(p.type))
			p_cloud.add_to_group(parent_group_id)

	def translate_by(self, vec):
		for p_g in self.pxl_groups:
			p_g.pxls = np.add(np.array(p_g.pxls), vec)

	def copy(self):
		return TomoObject( self.raw_cutobject, self.pxl_groups, self.best_vminfo, self.colorspan, self.mat4x4)
