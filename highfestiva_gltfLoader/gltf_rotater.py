import numpy as np
import trimesh
from gltf_primitives import gltfMesh, gltfPrimitive, gltfModel
from hf_skin_animator import SkinAnimator

class gltfHull:
	#def __init__(self, meshes: gltfMesh):
	#	verts = np.empty((1, 3), dtype=float)
	#	for m in meshes:
	#		for p in m.primitives:
	#			verts = np.append( verts, p.vertices, axis=0)
	#	point_cloud = trimesh.points.PointCloud(verts)
	#	self.chullmesh = point_cloud.convex_hull

	#def __init__(self, ani : SkinAnimator, primitives : gltfPrimitive):
	#	verts = np.empty((1, 3), dtype=float)
	#	for p in primitives:
	#		verts = np.append( verts, p.vertices, axis=0)
	#	point_cloud = trimesh.points.PointCloud(verts)
	#	self.chullmesh = point_cloud.convex_hull

	#def __init__(self, model : gltfModel):
	#	verts = np.empty((1, 3), dtype=float)
	#	for m in model.meshes:
	#		for p in m.primitives:
	#			verts = np.append( verts, p.vertices, axis=0)
	#	point_cloud = trimesh.points.PointCloud(verts)
	#	self.chullmesh = point_cloud.convex_hull

	def __init__(self, verts):
		point_cloud = trimesh.points.PointCloud(verts)
		self.chullmesh = point_cloud.convex_hull

class gltfRotater:
	def __init__(self, chull):
		self.chull = chull

	def get_matrix(self, rxryrz, max_height):
		M = self.chull.chullmesh

		vec1 = (M.bounds[0] + M.bounds[1]) * -0.5
		M.apply_translation( vec1)

		R3 = trimesh.transformations.euler_matrix(
			rxryrz[0],
			rxryrz[1],
			rxryrz[2],
			'syxz')
		V0 = M.vertices
		V1 = np.c_[ V0, np.ones(len(V0))]
		V1 = np.dot(R3, V1.T).T
		M.vertices = V1[:,0:3]

		z_scale = max_height / (M.bounds[1][2] - M.bounds[0][2])
		M.apply_scale(z_scale)

		vec2 = M.bounds[0] * -1
		M.apply_translation( vec2)

		D1 = np.eye(4)
		S2  = np.eye(4)
		D4 = np.eye(4)
		D1[0:3,3] 	= vec1
		S2[0:3,0:3] *= z_scale
		D4[0:3,3] 	= vec2

		return D4 @ S2 @ R3 @ D1
