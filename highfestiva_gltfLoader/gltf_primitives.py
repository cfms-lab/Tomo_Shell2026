import numpy as np

class gltfMesh:
	def __init__(self, name, primitives):
		self.name = name
		self.primitives = primitives


class gltfPrimitive:
	def __init__(self, name, material, triangles, vertices, normals, uvs, joints, weights):
		self.name 		= name
		self.material	= material
		self.triangles 	= triangles
		self.vertices 	= vertices
		self.normals 	= normals
		self.uvs		= uvs
		self.joints 	= joints
		self.weights	= weights

	def initial_transform(self, mat4x4):
		V  = self.vertices
		V1 = np.c_[ V, np.ones(len(V))]
		V1 = np.dot(mat4x4, V1.T).T
		self.vertices = V1[:,0:3]

class gltfModel:
	def __init__(self, name, nodes, ordered_node_indexes, meshes, animations, skins, teximages):
		self.name 		= name
		self.nodes		= nodes
		self.ordered_node_indexes = ordered_node_indexes
		self.meshes		= meshes #class gltfPrimitive
		self.animations = animations
		self.skins		= skins
		self.teximages	= teximages

	def initial_transform(self, mat4x4):
		for m in self.meshes:
			for p in m.primitives:
				p.initial_transform( mat4x4)
