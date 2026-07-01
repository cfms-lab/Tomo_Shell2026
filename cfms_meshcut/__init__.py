import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import trimesh
import numpy as np
import polyscope as ps
from copy import copy

from cut_colors import cutColorSpan, DefaultFilamentColors
from cut_group import CutGroup
from cut_function import cutFunction, cutType
from cut_object import CutObject


class CutManager:
	name = "cuts"
	hfManager = None #Todo: 그냥 trimesh로 대체하기.
	joints = None#이거 필요한가? 그냥 함수 파라미터로 받아도 될 듯.
	ps_raw_group = None #polyscope graph node for raw mesh

	def __init__(self, gltfAvatar,  max_height = None, rotation_angle=None):
		self.hfManager = gltfAvatar.manager
		if self.hfManager.animator: 		self.joints = self.hfManager.animator.joints
		if rotation_angle is not None: 	self.RxRyRz = rotation_angle
		self.tmesh = copy(gltfAvatar.tmesh)

	def choose_group_id_to_move_to(self, group_ids):
		if   group_ids[0] == group_ids[1]:	return group_ids[0]
		elif group_ids[1] == group_ids[2]:	return group_ids[1]
		else:								return group_ids[2]

	def skinweight_groups(self, V):
		#Rig skin-weight segmentation: assign each (tmesh) vertex to the body part of its
		#dominant rig joint. Uses the gltf skin/joints/weights directly, so it carries no
		#geometric/normal noise. Joint -> body part is by mixamo bone-name keyword.
		import numpy as np
		from scipy.spatial import cKDTree
		model = self.hfManager.model
		nodes = model.nodes
		skin  = model.skins[0]

		def part_of(name):
			n = name or ''
			if any(k in n for k in ('Hand', 'Arm', 'Shoulder')):	return 2 if 'Left' in n else 3
			if any(k in n for k in ('Leg', 'Foot', 'Toe')):			return 4 if 'Left' in n else 5
			if any(k in n for k in ('Head', 'Neck', 'Eye')):		return 0
			return 1 #Spine/Hips/root -> Bodice

		joint_part = np.array([part_of(getattr(nodes[ni], 'name', '')) for ni in skin.joints], dtype=int)

		#joints/weights live on model.meshes primitives (original vertex order); the matching
		#SKINNED vertex positions (in tmesh space) live on animator.skinned_primitives, in the
		#same nested (mesh, primitive) order. Pair them by index so the KD-tree is in tmesh space.
		ani = self.hfManager.animator
		skinned = ani.skinned_primitives if (ani and ani.skinned_primitives) else None
		P, L, i = [], [], 0
		for m in model.meshes:
			for p in m.primitives:
				if p.joints is not None and p.weights is not None:
					j = np.asarray(p.joints); w = np.asarray(p.weights)
					dom = j[np.arange(len(j)), np.argmax(w, axis=1)] #dominant local joint per vertex
					verts = np.asarray(skinned[i].vertices) if skinned is not None else np.asarray(p.vertices)
					P.append(verts); L.append(joint_part[dom])
				i += 1
		P = np.concatenate(P, axis=0); L = np.concatenate(L, axis=0)
		_, idx = cKDTree(P).query(np.asarray(V), k=1) #map (reindexed) tmesh vertices to nearest rig vertex
		return L[idx]

	def cut_mesh(self, cut_method):
		self.name =  f"{cut_method.name}_cut"

		self.cuts = []
		HF = self.hfManager
		T = self.tmesh
		J = self.joints
		V  = np.array( T.vertices, copy = True)
		Vn = np.array( T.vertex_normals, copy = True)
		F  = np.array( T.faces, copy = True)
		FC = np.array( T.triangles_center, copy = True)
		Fn = np.array( T.face_normals, copy = True)

		#B1, B2= HF.get_bone_pos() # parent/child xyz coordinates
		B1, B2 = HF.get_end_bone_pos() #계측용 5분할

		#prepare polyscope graph
		new_ps_id = ps.create_group( f"{self.name}_G")
		colorspan = cutColorSpan(DefaultFilamentColors)
		cutobjects = []
		color_id = 0

		if cut_method.type.value == cutType.no_cut.value:#for no_cut option
			object_name = f"{self.name}_sub_no_cut"
			new_object = CutObject( object_name, T, colorspan, color_id)
			cutobjects.append( new_object) #prepare rendering data
			newcut = CutGroup( self.name, new_ps_id, self.joints, cutobjects )
			self.cuts.append( newcut)
			return newcut

		#Do (K-Means) clustering
		if cut_method.type.value == cutType.bone_skinweight.value:#rig skin-weight segmentation (uses gltf joints/weights, not a distance metric)
			k_groups   = self.skinweight_groups( V)
			bPerVertex = True
		else:
			k_groups, bPerVertex = cutFunction(
				cut_method,
				V , FC,
				Vn, Fn,
	   		bonetip1   = B1,
				bonetip2   = B2
	 			)

		#mesh-connectivity label smoothing (removes isolated noise / fragmented parts)
		if cut_method.type.value == cutType.bone_p2bdist3.value and bPerVertex:
			from cut_math import smooth_vertex_labels
			k_groups = smooth_vertex_labels( k_groups, T, iterations=3)

		#classify elements w.r.t. "k_groups" ID
		faces_sequences = [[] for _ in range(len(k_groups))]
		if bPerVertex:
			for face_id, face in enumerate(F):#
				vtx = face[0:3] #three triangle vertex IDs
				vtx_groups = k_groups[vtx]
				group_id = self.choose_group_id_to_move_to( vtx_groups)
				faces_sequences[group_id].append( face_id)
		else:#perFace
			for face_id, group_id in enumerate(k_groups):
				faces_sequences[group_id].append( face_id)

		#split mother mesh using trimesh.submesh()
		bSplitFarAway = False#debug
		for f_s_id, f_s in enumerate(faces_sequences):
			if f_s:
				T1 = trimesh.util.submesh( T, [f_s], repair=False, only_watertight=False)[0]

				if bSplitFarAway:
					T1_split = T1.split(only_watertight=False)# 엉뚱하게 떨어져 있는 조각들은 독립시켜 따로 등록한다.
					for t_s in T1_split:
						if len(t_s.vertices) > 3:
							object_name = f"{self.name}_sub{f_s_id:02d}{color_id:02d}"
							new_object = CutObject( object_name, t_s, colorspan, color_id)
							cutobjects.append( new_object) #prepare rendering data
							color_id += 1
				else:
					object_name = f"{self.name}_sub{f_s_id:02d}{color_id:02d}"
					new_object = CutObject( object_name, T1, colorspan, color_id)
					cutobjects.append( new_object) #prepare rendering data
					color_id += 1

		newcut = CutGroup( self.name, new_ps_id, self.joints, cutobjects )
		self.cuts.append( newcut)

		return newcut

