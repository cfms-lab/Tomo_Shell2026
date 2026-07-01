import numpy as np
import networkx as nx
from trimesh.curvature import discrete_mean_curvature_measure
import potpourri3d as pp3d
from cfms_bodym.bodym_functions import *
from cfms_meshcut.cut_object import CutObject
from cfms_meshcut.cut_colors import cutColorSpan, DefaultFilamentColors


class BodyMeasure:
	def __init__(self, avatar, cut_group, bodyM = None):
		self.avatar = avatar
		self.WholeBody = CutObject( f"{avatar.manager.filename}_WB", avatar.tmesh, DefaultFilamentColors, 0)
		self.WholeBody.BodyPartID = BodyPart.WholeBody

		self.cut_group		= cut_group
		self.BodyPart = [BodyPart.Bodice for _ in range(6)] #기본적으로는 6개가 기준이나, 최종 계측할 때에는 Torso를 추가해서 7개를 쓴다.
		self.features = [] 	#특징점의 좌표
		self.girths  = [] 	#원형 단면의 둘레 길이
		self.sizelines  = []#줄자로 잰 길이
		self.cutlines = []	#for debug

		self.prepare_graph()
		self.prepare_basis_vec()
		if not bodyM:
			self.prepare_BP_ID()

	def measure(self):
		self.find_girths()
		self.find_feature_points()
		self.find_lengths()

	def prepare_graph(self):
		edges 	= self.avatar.tmesh.edges_unique
		length	= self.avatar.tmesh.edges_unique_length
		self.G = nx.Graph()
		for edge, L in zip(edges, length):
				self.G.add_edge(*edge, length=L)

	def getBPVec(self, lm):
		vec_name = lm[2]
		if vec_name == BPVector.BoneDir:
			from sklearn.preprocessing import normalize
			M = self.avatar.manager
			B0 = M.get_bone_pos_by_name( get( lm, LandMark.From))
			B1 = M.get_bone_pos_by_name( get( lm, LandMark.To))
			vec = normalize( [B1-B0] )[0]
			return vec
		if vec_name == BPVector.Up:
			return self.up
		elif vec_name == BPVector.Down:
			return self.up * -1.
		elif vec_name == BPVector.Right:
			return self.right
		elif vec_name == BPVector.Left:
			return self.right * -1.
		elif vec_name == BPVector.Front:
			return self.front
		elif vec_name == BPVector.Back:
			return self.front * -1.
		elif vec_name == BPVector.Head:
			return self.head
		elif vec_name == BPVector.Bodice:
			return self.bodice
		elif vec_name == BPVector.LeftArm:
			return self.L_arm
		elif vec_name == BPVector.RightArm:
			return self.R_arm
		elif vec_name == BPVector.LeftLeg:
			return self.L_leg
		elif vec_name == BPVector.RightLeg:
			return self.R_leg

	def prepare_basis_vec(self):
		M = self.avatar.manager
		self.right 	= M.get_unit_vec( 'mixamorig:LeftShoulder',		'mixamorig:RightShoulder')
		self.up			= M.get_unit_vec( 'mixamorig:Spine', 			'mixamorig:HeadTop_End')
		self.front	=	np.cross( self.up, self.right)

		self.L_arm  = M.get_unit_vec( 'mixamorig:LeftHand',		'mixamorig:LeftArm')
		self.R_arm  = M.get_unit_vec( 'mixamorig:RightHand',	'mixamorig:RightArm')

		self.L_leg  = M.get_unit_vec( 'mixamorig:LeftFoot',		'mixamorig:LeftUpLeg')
		self.R_leg  = M.get_unit_vec( 'mixamorig:RightFoot',	'mixamorig:RightUpLeg')

		self.head   = M.get_unit_vec( 'mixamorig:Neck', 			'mixamorig:Head')
		self.bodice	= M.get_unit_vec( 'mixamorig:Spine',			'mixamorig:Spine2')

	def prepare_BP_ID(self):
		C_O = self.cut_group.cutobjects
		for c_o in C_O:
			c_o.BodyPartID = BodyPart.NotKnown #초기화

		M = self.avatar.manager
		bp_data = BodyPart_data.copy()
		while len(bp_data) > 0:
			bp_id, bp_name, ft_name  = bp_data.pop()
			ft_pos = M.get_bone_pos_by_name(ft_name)
			ft2co_dist = np.ones(6) * 1e5
			for id, c_o in enumerate(C_O):
				if c_o.BodyPartID == BodyPart.NotKnown:
					ft2co_dist[id] = get_p2p_dist( ft_pos, c_o.tmesh.centroid)
			nearest_id = np.argmin(ft2co_dist)
			C_O[nearest_id].BodyPartID = bp_id
			C_O[nearest_id].name = bp_name + "__"+C_O[nearest_id].name #for rendering


	def get_girth(self, name):
		for girth in self.girths:
			if girth.name == name:
				return girth.slice

	def get_feature_pos(self, name):
		for ft in self.features:
			if ft.name == name:
				return np.array(ft.pos)

	def set_feature_pos(self, name, new_pos):
		for ft in self.features:
			if ft.name == name:
				ft.pos = new_pos
				return

	def get_nearest_v_id_to_feature(self, vtx0, name):
		pos = self.get_feature_pos( name)
		dist = get_p2vtx_dist( pos, vtx0)
		min_id = np.argmin( dist)
		return min_id

	def getBP(self, bp_id):
		if bp_id == BodyPart.WholeBody:
			return self.WholeBody

		for c_o in self.cut_group.cutobjects:
			if c_o.BodyPartID == bp_id:
				return c_o
		return None


	def find_girths(self):
		M = self.avatar.manager
		for lm in girth_data:
			c_o = self.getBP( get( lm, LandMark.Part))
			if c_o:
				B0 = M.get_bone_pos_by_name( get( lm, LandMark.From))
				B1 = M.get_bone_pos_by_name( get( lm, LandMark.To))
				t  = get( lm, LandMark.param)
				origin = B0 * t + B1 * (1.- t)
				normal = self.getBPVec( lm)
				slice	 = c_o.tmesh.section(plane_origin= origin, plane_normal= normal)
				if slice:
					slice  = get_closest_boundary( slice, origin)
					if slice:
						self.girths.append( GirthSlice( get( lm, LandMark.Name), slice))


	def find_feature_points(self):
		self._find_addams_apple()
		self._find_breast_point()
		self._find_crotch_point()
		self._find_finger_tip()

		for ft in feature_points_data:
			girth = self.get_girth(ft[1])
			if girth:
				self.features.append( FeaturePos( ft[0], get_vtx_to_dir( girth.vertices, self.getBPVec(ft))))

		self._adjust_waist_points()


	def _find_addams_apple(self):
		M = self.avatar.manager
		c_o_head			= self.getBP( BodyPart.Head)
		head 					= M.get_bone_pos_by_name( 'mixamorig:Head')
		head_v_slice	= c_o_head.tmesh.section(plane_origin = head, plane_normal= self.right)
		self.cutlines.append(	CutLine('cutline_Head', head_v_slice))
		self.features.append( FeaturePos( "head_tip",  		get_vtx_to_dir( head_v_slice.vertices, self.up - self.front * 0.1)))
		self.features.append( FeaturePos( "head_rear",  	get_vtx_to_dir( head_v_slice.vertices, self.front * -1.)))
		self.features.append( FeaturePos( "chin_lowest",  get_vtx_to_dir( head_v_slice.vertices, self.front - self.up * 0.5)))


	def _find_breast_point(self):
		c_o_bodice 	= self.getBP( BodyPart.Bodice)
		nb_vtx = self.get_girth( 'bust_girth').vertices
		G_C 				= discrete_mean_curvature_measure(c_o_bodice.tmesh, nb_vtx, radius = .01)
		max_ids			= np.argsort(G_C)
		self.features.append( FeaturePos( f"breast{0}", nb_vtx[max_ids[-1]] ))
		self.features.append( FeaturePos( f"breast{1}", nb_vtx[max_ids[-2]] ))


	def _find_crotch_point(self):
		M = self.avatar.manager
		c_o_bodice			= self.getBP( BodyPart.Bodice)
		spine 					= M.get_bone_pos_by_name( 'mixamorig:Spine')
		self.bodice_v_slice	= c_o_bodice.tmesh.section(plane_origin = spine, plane_normal= self.right)
		self.cutlines.append( CutLine( 'cutline_Bodice', self.bodice_v_slice))
		self.features.append( FeaturePos( "crotch", get_vtx_to_dir( self.bodice_v_slice.vertices, self.bodice * -1.)))

	def _find_finger_tip(self):
		c_o_rArm 			= self.getBP( BodyPart.RightArm)
		self.features.append( FeaturePos( "R_fingertip", get_vtx_to_dir( c_o_rArm.tmesh.vertices, self.R_arm * -1.)))
		c_o_lArm 			= self.getBP( BodyPart.LeftArm)
		self.features.append( FeaturePos( "L_fingertip", get_vtx_to_dir( c_o_lArm.tmesh.vertices, self.L_arm* -1.)))


	def translate_by(self,vec):
		vec = vec

	def _adjust_waist_points(self):#수직 수평 절단선의 교점으로 수정한다.
		vtx 		= self.bodice_v_slice.vertices
		for ft_name in ['F_waist', 'rear_waist', 'rear_hip']:
			ft_pos 	= self.get_feature_pos( ft_name)
			dist 		= get_p2vtx_dist( ft_pos, vtx)
			min_id 	= np.argmin( dist)
			self.set_feature_pos( ft_name, vtx[min_id])

	def find_lengths(self):
		# Surface (tape-measure) lengths are measured as EXACT edge-flip geodesic paths
		# (Sharp & Crane 2020) on the body mesh. This is more accurate than the heat-method
		# distance, which smooths and tends to over/under-estimate short on-body paths.
		# Build the geodesic solver ONCE and reuse it for every length item: the solver's
		# precomputation is the expensive part, so re-creating it per item was wasteful.
		T = self.avatar.tmesh
		self._geoV = np.array(T.vertices)
		self._geo_solver = pp3d.EdgeFlipGeodesicSolver(self._geoV, np.array(T.faces))
		for d in length_data:
			path_pts = self.shortest_path( d[1])
			self.sizelines.append( SizeLine( d[0], path_pts, get_pts_length(path_pts)))

	def shortest_path(self, features):#slice는 하나짜리 곡선이라고 가정. 폐곡선이 아닐 수도 있음.
   	# https://github.com/nmwsharp/potpourri3d#mesh-geodesic-paths

		#논문 그림용(최단 경로)-------------------------
		#vtx0 = self.avatar.tmesh.vertices.copy()
		#feature_pos1 = self.get_feature_pos(features[0])
		#feature_pos2 = self.get_feature_pos(features[-1])

		#ft1_to_vtx_dist = np.linalg.norm( np.subtract( np.array(vtx0),  feature_pos1 ), axis=1)
		#ft2_to_vtx_dist = np.linalg.norm( np.subtract( np.array(vtx0),  feature_pos2 ), axis=1)
		#ft1_id = np.argmin( ft1_to_vtx_dist)
		#ft2_id = np.argmin( ft2_to_vtx_dist)

		#path_id = nx.shortest_path( self.G, source=ft1_id, target=ft2_id, weight="length")
		#new_slice = trimesh.path.Path3D(
		#		entities = [ trimesh.path.entities.Line(np.array(path_id)) ],
		#		vertices = vtx0)
		#new_slice.remove_unreferenced_vertices()
		#return new_slice.vertices
		#-----------------------------------

		# reuse the pre-built exact edge-flip geodesic solver (see find_lengths)
		V = self._geoV
		path_solver = self._geo_solver

		paths = np.empty((0,3))
		for ft1, ft2 in zip( features[:-1], features[1:]):
			f_id1 = self.get_nearest_v_id_to_feature( V, ft1)
			f_id2 = self.get_nearest_v_id_to_feature( V, ft2)
			path = path_solver.find_geodesic_path(v_start=f_id1, v_end=f_id2)# path_pts is a Vx3 numpy array of points forming the path
			paths = np.append(paths, np.array(path), axis=0)

		return paths


	def add_to(self, renderer):
		PS0 = self.cut_group.parent_ps
		ft_group = renderer.create_group("features")
		gt_group = renderer.create_group("girths")
		ln_group = renderer.create_group("lengths")
		PS0.add_child_group(ft_group )
		PS0.add_child_group(gt_group )
		PS0.add_child_group(ln_group )

		print("Features heights (Red dots):")
		for ft in self.features:
			mat4x4 = trimesh.transformations.translation_matrix(ft.pos)
			mark = trimesh.primitives.Sphere( radius = .75, transform = mat4x4)
			mesh = renderer.register_surface_mesh(ft.name, mark.vertices, mark.faces, color = ( 1., 0., 0.))
			mesh.add_to_group(ft_group)
			print(f"  {ft.name}={FStr(ft.pos[2])}")

		print("Girths (blue circles):")
		for girth in self.girths:
			curve = renderer.register_curve_network(girth.name, radius=0.001, color = ( 0., 0., 1.),
					nodes = girth.slice.vertices, edges = girth.slice.vertex_nodes)
			curve.add_to_group(gt_group)
			print(f"  {girth.name}={FStr(girth.slice.length)}")
			#len = get_pts_length( girth.slice.vertices)
			#print(f"  {girth.name}={FStr(len)}")

		print("Lengths (green curves):")
		for s_l in self.sizelines:
			curve = renderer.register_curve_network(s_l.name, radius=0.001, color = ( 0., .5, .1),
					nodes = s_l.points, edges = "line")
			curve.add_to_group(ln_group)
			print(f"  {s_l.name}={FStr(s_l.length)}")

		#for c_l in self.cutlines:
		#	renderer.register_curve_network( c_l.name, radius=0.001, color = ( 1., 1., 0.),
		#			nodes =	c_l.slice.vertices, edges = c_l.slice.vertex_nodes)


