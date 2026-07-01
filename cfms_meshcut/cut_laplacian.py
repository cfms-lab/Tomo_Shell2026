from cut_group import CutGroup
from cut_object import CutObject
import trimesh
from trimesh.grouping import group_rows
from trimesh.smoothing import laplacian_calculation, filter_taubin
import numpy as np

def extract_acute_faces(T: trimesh.Trimesh):
	#(1) boundary edge가 두 개인 삼각형(=acute triangle)을 찾는다.
	boundary_edges		= trimesh.grouping.group_rows(T.edges_sorted, require_count=1)

	boundary_edge_mask = np.unique( np.array(boundary_edges).flatten())
	bBoundaryEdge = np.full( T.edges.shape[0], False)
	bBoundaryEdge[boundary_edge_mask] = True

	boundary_faces 		= T.edges_face[boundary_edges]
	acute_faces_mask 	= trimesh.grouping.group_rows(boundary_faces, require_count=2)
	acute_faces 			= acute_faces_mask[:,0]
	for a_f in acute_faces:#ToDo: vectorize
		tri_center = T.triangles_center[a_f]
		u_edges = T.faces_unique_edges[a_f]

		for edge in u_edges:
			if not bBoundaryEdge[edge]:#이게 꼭지 마주보는 변이다.
				#edge = tri_center#debug
				break

	return T

def subdivide_acute_triangle( c_g : CutGroup):
	smoothed_c_g = c_g.copy('acute_')

	for c_o in smoothed_c_g.cutobjects:
		T = c_o.tmesh
		T = extract_acute_faces( T)

	return smoothed_c_g


def get_boundary_faces(T :trimesh.Trimesh, faces_sequences):
	b_f_list = np.empty((0), dtype=np.int64)
	for f_s in faces_sequences:
		if f_s:
			subT_face0 = f_s[0] #시작 face 번호
			subT = trimesh.Trimesh(
          vertices = T.vertices,
          faces = T.faces[f_s],
          process  = False, validate  = False)
			sub_boundary_edges		= trimesh.grouping.group_rows(subT.edges_sorted, require_count=1)
			sub_boundary_faces 		= np.unique( np.sort( subT.edges_face[sub_boundary_edges]))
			sub_boundary_faces 	+= subT_face0
			b_f_list = np.append( b_f_list, sub_boundary_faces)

	b_f_list = np.unique( np.sort(b_f_list))
	return b_f_list
