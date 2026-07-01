import numpy as np

from gltf_loader import load_model
from hf_mesh import hfMesh
from hf_textures import hfTextures
from hf_skin_animator import SkinAnimator

def unit_vector_normalize(v):
	norm = np.linalg.norm(v)
	if norm == 0:	return v  # 0 벡터의 경우 그대로 반환
	return v / norm


class hfManager():
	def __init__(self, renderer, _fname, max_height):
		self.renderer 	= renderer
		self.filename	= _fname
		self.model 		= load_model(_fname)  #raw mesh (without motion)
		self.textures	= hfTextures(renderer, self.model.teximages)
		self.hfmeshes 	= [] #mesh with motion offset

		self.animator	= SkinAnimator(self.renderer, self.model)
		self.animator.start_animate()

		#debug print
		from cfms_tomo.tomo_io import FStr
		for j in self.animator.joints:
			print(j.parent_name, FStr(j.parent_xyz,3), '-->',  j.name, FStr(j.xyz,3))

	def animate(self, delta_time):
		self.animator.play_animation( delta_time)
		self.animator.init_render( self.model.nodes)

	def rebuild_meshes(self):
		# release previous meshes
		if self.hfmeshes:
			for mesh in self.hfmeshes:	del mesh
			self.hfmeshes.clear()# 굳이 clear할 필요가 있나?
		# build new ones
		if self.animator.skinned_primitives:#텍스쳐 있는 경우
			for p_id, p in enumerate(self.animator.skinned_primitives):
				if p.material:
					tex_id = p.material
					texname = self.model.teximages[tex_id].name
					meshname = f"{self.model.name}_{tex_id}"
					tex_data = self.textures.get(texname)
					self.hfmeshes.append( hfMesh(self.renderer, meshname, p, tex_data))
				else:
					meshname = f"{self.model.name}_{p_id}"
					self.hfmeshes.append(hfMesh(self.renderer, meshname, p, None))

		else:#텍스쳐 없는 경우
			for m_id, m in enumerate(self.model.meshes):
				for p_id, p in enumerate( m.primitives):
					meshname = f"{self.model.name}_{m_id}_{p_id}"
					self.hfmeshes.append(hfMesh(self.renderer, meshname, p, None))

	def get_bone_pos(self):
		child_xyz = [] # coordinates of bone
		parent_xyz = [] #plane normal vector, pointing to the parent direction
		for j in self.animator.joints:
			if len(j.parent_name) > 0:
				child_xyz.append( j.xyz)
				parent_xyz.append( j.parent_xyz)
		child_xyz = np.array(child_xyz)
		parent_xyz = np.array(parent_xyz)
		return parent_xyz, child_xyz

	def add_to(self, renderer, parent_gp=None):
		#show hfMesh
		for mesh in self.hfmeshes:
			ps_mesh = mesh.add_to(renderer)
			if parent_gp: ps_mesh.add_to_group(parent_gp)

		#show joints
		self.animator.add_to(renderer, parent_gp)


    #bodyM functions
	def get_unit_vec(self, b0, b1):
		vec0 = self.get_bone_pos_by_name(b0)
		vec1 = self.get_bone_pos_by_name(b1)
		return unit_vector_normalize( np.array(vec1) - np.array(vec0))

	def get_bone_pos_by_name(self, bone_name):
		if bone_name == "root": return self.animator.joints[0].parent_xyz

		for j in self.animator.joints:
			if j.name == bone_name:
				return j.xyz

	def get_end_bone_pos(self):
		child_xyz = [] # coordinates of bone
		parent_xyz = [] #plane normal vector, pointing to the parent direction

		#bone_pairdist_0 = ['mixamorig:HeadTop_End','mixamorig:LeftShoulder','mixamorig:RightShoulder','mixamorig:LeftUpLeg'	,'mixamorig:RightUpLeg'	,'mixamorig:LeftUpLeg']
		#bone_pairdist_1 = ['mixamorig:Neck','mixamorig:LeftHand','mixamorig:RightHand','mixamorig:LeftLeg'	,'mixamorig:RightLeg'	,'mixamorig:RightUpLeg']
		#for b0, b1 in zip( bone_pairdist_0, bone_pairdist_1):
		#	child_xyz.append( self.get_bone_pos_by_name(b0))
		#	parent_xyz.append( self.get_bone_pos_by_name(b1))

		bone_p2bdist_0 = [
      'mixamorig:HeadTop_End'
      ,'mixamorig:LeftForeArm'
			,'mixamorig:RightForeArm'
			,'mixamorig:LeftFoot'
			,'mixamorig:RightFoot'
			,'mixamorig:Neck'
		]

		bone_p2bdist_1 = [
			'mixamorig:Head'
      ,'mixamorig:LeftHand'
			,'mixamorig:RightHand'
			,'mixamorig:LeftLeg'
			,'mixamorig:RightLeg'
			,'root'
		]

		for b0, b1 in zip( bone_p2bdist_0, bone_p2bdist_1):
			child_xyz.append( self.get_bone_pos_by_name(b0))
			parent_xyz.append( self.get_bone_pos_by_name(b1))

		child_xyz = np.array(child_xyz)
		parent_xyz = np.array(parent_xyz)
		return parent_xyz, child_xyz
