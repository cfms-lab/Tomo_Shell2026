import glm
import numpy as np
from gltf_loader import *

class hfJointInfo:
	name = ''
	parent_name = ''
	xyz = np.zeros(3)
	parent_xyz = np.zeros(3)

	def __init__(self, name, xyz, parent_name, parent_xyz):
		self.name = name
		self.parent_name = parent_name
		self.xyz  = xyz
		self.parent_xyz = parent_xyz

class SkinAnimator:
	def __init__(self, renderer, model):
		self.renderer = renderer
		self.model = model
		self.animation = None
		self.time = -1
		self.time_duration = 1
		self.speed = 1.0
		self.mode = "single"
		self.skinned_primitives = []
		self.homogenized_vertices = []  # input for skinning
		self.skinned_vertices = []  # output for skinning
		self.init_opt_skin_vertices()

		#openGL rendering
		self.bones = []
		self.joints = []

	def init_opt_skin_vertices(self):
		for mesh in self.model.meshes:
			for primitive in mesh.primitives:
				vs = primitive.vertices
				# homogenize vertices
				hvertices = np.append(
					vs, np.array([[1.0]] * len(vs), dtype=np.float32), axis=1
				)
				self.homogenized_vertices.append(hvertices)
				self.skinned_vertices.append(hvertices.copy())

	def start_animate(self, mode="loop", speed=1.0, animation_index=0):
		self.mode = mode
		self.speed = speed
		self.time = 0
		if len(self.model.animations)>0:
			self.animation = self.model.animations[animation_index]
			self.time_duration = self.animation.duration
		## print('starting transform animation')

	def play_animation(self, delta_time):
		if not self.animation: return
		if self.time < 0:			return

		self.apply_animation()
		self.time += delta_time * self.speed
		if self.time >= self.time_duration:
			if self.mode == "loop":
				self.time %= self.time_duration  # restart
			else:
				self.time = -1  # stop animation

	def apply_animation(self):
		self.animate_nodes()
		self.calc_node_transforms()
		self.create_animated_primitives()

	def create_animated_primitives(self):
		"""
		Only create primitives once, after that we update the vertex array in-place using a numpy stride trick.
		"""
		add_primitives = True if not self.skinned_primitives else False
		joint_matrices = self.calc_joint_matrices()
		primitive_index = 0
		for mesh in self.model.meshes:
			for primitive in mesh.primitives:
				homogenized_vertices = self.homogenized_vertices[primitive_index]
				skinned_vertex_buf = self.skinned_vertices[primitive_index]
				primitive_index += 1
				apply_skinning_to_vertices(
					homogenized_vertices,
					skinned_vertex_buf,
					primitive.joints,
					primitive.weights,
					joint_matrices,
				)
				if add_primitives:
					# drop the homogenized column
					skinned_vertices = np.lib.stride_tricks.as_strided(
						skinned_vertex_buf,
						shape=(len(skinned_vertex_buf), 3),
						strides=(4 * 4, 4),
					)
					# create a new primitive using the skinned vertices
					self.skinned_primitives.append(
						gltfPrimitive(
							primitive.name,
							primitive.material,
							primitive.triangles,
							skinned_vertices,
							primitive.normals,
							primitive.uvs,
							None,
							None,
						)
					)

	def animate_nodes(self):
		"""
		Here we update all animated nodes by setting translation, rotation and scale as applicable.
		"""
		animation = self.animation
		for channel in animation.channels:
			sampler = animation.samplers[channel.sampler]
			keyframe_times = sampler.keyframe_times
			keyframe_values = sampler.keyframe_values

			# Interpolate the values based on current time
			interpolated_value = interp_anim_vec(
				channel.path,
				self.time,
				sampler.interpolation,
				keyframe_times,
				keyframe_values,
			)

			# Update the node's transform (translation, rotation, scale)
			if channel.path == "translation":
				self.model.nodes[channel.node].translation = interpolated_value
			elif channel.path == "rotation":
				self.model.nodes[channel.node].rotation = interpolated_value
			elif channel.path == "scale":
				self.model.nodes[channel.node].scale = interpolated_value

	def calc_node_transforms(self):
		"""
		Assume the nodes' translation, rotation and scale has already been set by the animation update.
		Set the global transform from each node's T*R*S, and if it has a parent, use that too.
		"""
		for node in self.model.nodes:
			node.transform = calc_local_transform(node)
		for node_index in self.model.ordered_node_indexes:
			node = self.model.nodes[node_index]
			parent_index = node.parent_index
			if parent_index >= 0:
				parent_node = self.model.nodes[parent_index]
				node.transform = np.dot(parent_node.transform, node.transform)

	def init_render(self, gltf_nodes):
		self.bones = []
		self.joints = []
		for node_index in self.model.ordered_node_indexes:
			node = self.model.nodes[node_index]
			if node.parent_index >=0:#뼈대 없는 메쉬의 경우는 []이다.
				node_xyz = node.transform[:,-1][0:3]
				parent_index = node.parent_index
				if parent_index >= 0:
					parent_node = self.model.nodes[parent_index]
					if parent_node.parent_index >=0 :
						parent_xyz = parent_node.transform[:,-1][0:3]
						self.bones.append( np.concatenate((parent_xyz, node_xyz), axis=0).flatten())
						j_info = hfJointInfo( node.name, node_xyz, parent_node.name, parent_xyz)
						self.joints.append( j_info)


	def render(self, shader):#OpenGL version. use add_to() instead
		bone_lines = np.array(self.bones).flatten().astype("f4")
		self.bone_vbo = self.ctx.buffer( bone_lines.tobytes())
		self.bone_vao = self.ctx.vertex_array( shader, [(self.bone_vbo, "3f", "in_position")])
		self.bone_vao.render(mode=mgl.LINES)

		for jinfo in self.joints:
			cube(size = (0.05, 0.05, 0.05), normals=True, center = jinfo.xyz ).render( shader)

	def add_to(self, renderer, parent_gp=None):
		J = self.joints
		if(len(J)==0): return

		bone = renderer.register_curve_network(name = "_joints",
				nodes = joints_to_np_vertices( J), edges="segments", enabled = False)

		bone_gp  = renderer.create_group("_bone")
		bone.add_to_group(bone_gp)
		if parent_gp: parent_gp.add_child_group( bone_gp)
		#bone_gp.set_show_child_details(False)

		for j in J:
			ball = trimesh.primitives.Sphere( radius = 2., center = j.xyz, subdivisions = 1)
			ps_ball = renderer.register_surface_mesh(j.name, ball.vertices, ball.faces, enabled = False)
			ps_ball.add_to_group(bone_gp)



	def calc_joint_matrices(self):
		"""
		Use the node transforms as already calculated when animating the joints, and create transforms for each joint.
		"""
		assert len(self.model.skins) == 1
		for skin in self.model.skins:
			joint_matrices = []
			# For each joint, calculate the skinning matrix
			for joint_index, inverse_bind_matrix in zip(
				skin.joints, skin.inverse_bind_matrices
			):
				# Get the global transformation of the joint (after applying animation)
				node = self.model.nodes[joint_index]
				joint_matrix = np.dot(
					node.transform, inverse_bind_matrix.reshape((4, 4)).T
				)
				joint_matrices.append(joint_matrix)
			return joint_matrices
		return []

	def initial_transform( self, mat4x4):
		for j in self.joints:
			j.xyz = (mat4x4 @ np.append( j.xyz, 1.))[0:3]
			j.parent_xyz = (mat4x4 @ np.append( j.parent_xyz, 1.))[0:3]


#@njit
def apply_skinning_to_vertices(
	vertices, out_vertex_buf, joint_indices, vertex_weights, joint_matrices
):
	# For each vertex, apply skinning
	for i, (vertex, vjoint, vweight) in enumerate(
		zip(vertices, joint_indices, vertex_weights)
	):
		# numba isn't to bright, so we loop unroll ourselves
		# numba complains here that performance would improve if arrays were contigous. I think they are
		# C-contigous, so I assume they have to be F-contigous for SciPy BLAS?
		skinned_vertices = [
			np.dot(joint_matrices[vjoint[0]], vertex),
			np.dot(joint_matrices[vjoint[1]], vertex),
			np.dot(joint_matrices[vjoint[2]], vertex),
			np.dot(joint_matrices[vjoint[3]], vertex),
		]
		skinned_vertex = (
			skinned_vertices[0] * vweight[0]
			+ skinned_vertices[1] * vweight[1]
			+ skinned_vertices[2] * vweight[2]
			+ skinned_vertices[3] * vweight[3]
		)
		# skinned_vertices = np.array([np.dot(joint_matrices[joint_index], vertex) for joint_index in vjoint])
		# skinned_vertex = np.dot(skinned_vertices.T, vweight)
		out_vertex_buf[i] = skinned_vertex


def calc_local_transform(node):
	# Construct transformation matrix from node's translation, rotation, and scale
	translation = glm.mat4()
	rotation = glm.mat4()
	scale = glm.mat4()
	if hasattr(node, "translation") and node.translation is not None:
		translation = glm.translate(translation, node.translation)
	if hasattr(node, "rotation") and node.rotation is not None:
		rotation = glm.mat4_cast(node.rotation)
	if hasattr(node, "scale") and node.scale is not None:
		scale = glm.scale(scale, glm.vec3(node.scale))
	# Global transform = T * R * S
	transform = translation * rotation * scale
	return np.array(transform)


def interp_anim_vec(path, t, interpolation, keyframe_times, keyframe_values):
	a, b, t = get_lerp(t, keyframe_times)
	a = (
		glm.quat(keyframe_values[a, [3, 0, 1, 2]])
		if path == "rotation"
		else glm.vec3(keyframe_values[a])
	)
	b = (
		glm.quat(keyframe_values[b, [3, 0, 1, 2]])
		if path == "rotation"
		else glm.vec3(keyframe_values[b])
	)
	if interpolation == "STEP":
		return a
	elif interpolation == "LINEAR":
		if path == "rotation":
			# slerp quaternions
			return glm.slerp(a, b, t)
		return glm.lerp(a, b, t)
	assert False, "bad interpolation"


def get_lerp(t, keyframe_times):
	for i, (t0, t1) in enumerate(
		zip(np.append([0.0], keyframe_times[:-1]), keyframe_times)
	):
		if t0 <= t < t1:
			j = (i + 1) % len(keyframe_times)
			t = (t - t0) / (t1 - t0)
			return i, j, t
	return 0, 0, 0

def joints_to_np_vertices( joints):
	V = []
	for j in joints:
		if j.parent_name is not None:
			V.append( j.parent_xyz)
			V.append( j.xyz)
	return np.array(V)
