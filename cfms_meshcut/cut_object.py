import numpy as np
from typing import Optional
import trimesh

class CutObject:

	def __init__(self, name, tmesh : trimesh.Trimesh, color_span, color_id, t_o = None):
		self.ps_id = -1
		self.name 			= name
		self.tmesh			= tmesh
		self.color_span		= color_span
		self.color_id		= color_id# % color_span.n_color
		self.tomo_object 	= t_o.copy() if t_o else []# optimal orientation info.

	def add_to(self, ps, ps_mother_group, colorspan):
		color 		= colorspan.get_color_float(self.color_id)

		target_group = None
		node_name = ''
		if self.tomo_object:#pxls 를 가지는 경우 (tomo)
			target_group =  ps.create_group(self.name)
			ps_mother_group.add_child_group(target_group )
			node_name = f"{self.name}_mesh"
			self.tomo_object.add_to(ps, target_group)
		else:# pxls 없는 경우 (cut, shell)
			target_group = ps_mother_group
			node_name = self.name

		self.ps_id = ps.register_surface_mesh(
				name = node_name,#name = 빼면 안됨
				vertices = self.tmesh.vertices,
				faces = self.tmesh.faces,
				color = color )
		self.ps_id.add_to_group(target_group)

		return self.ps_id

	def translate_by(self, vec):#for rendering(box-packing)
		self.tmesh.apply_translation( vec)
		#tomo_results도 옮겨 준다.
		if self.tomo_object:
			self.tomo_object.translate_by( vec)


	def save(self, dir, file_type):
		CS = self.color_span
		color_str 	= CS.get_color_str(self.color_id)
		fname 		= f"{dir}{color_str}_{self.name}_best.{file_type}"
		mtl_name 	= f"{color_str}_{self.name}_best.mtl"

		T  			= self.tmesh
		color 		= CS.get_color_uint8(self.color_id % CS.n_color)
		T.visual 	= trimesh.visual.TextureVisuals() # T.visual.kind = 'texture' 속성이 있어야 trimesh가  .mtl 저장한다.
		T.visual.material = trimesh.visual.material.SimpleMaterial(# 그 후에 색상 넣어야 한다.
      		ambient  = color,
        	diffuse  = color,
         	specular = color)

		T.export(file_obj = fname, file_type='obj', mtl_name = mtl_name)


	def transform(self,mat):#최적 회전값(t_o)을 이용해 메쉬(tmesh)를 회전시킨다.
		self.name = self.name + '_rotated'
		if mat is None:
			print("Error:  mat4x4 is None. ", self.name)
		else:
			self.tmesh = self.tmesh.apply_transform(mat)

	def GetMss(self):
		if self.tomo_object:
			return self.tomo_object.best_vminfo.GetMss()
		return 0