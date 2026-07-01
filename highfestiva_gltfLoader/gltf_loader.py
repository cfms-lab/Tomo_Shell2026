import os
import trimesh
import pygltflib
import numpy as np
from pathlib import Path
from collections import namedtuple

from hf_textures import TextureInfo
from hf_mesh import group_by_N
from gltf_primitives import *


#gltfModel            = namedtuple('Model', 'name nodes ordered_node_indexes meshes animations skins teximages')
#Mesh             = namedtuple('Mesh', 'name primitives')
#Primitive        = namedtuple('Primitive', 'name material triangles vertices normals uvs joints weights')
AnimationSampler = namedtuple('AnimationSampler', 'interpolation keyframe_times keyframe_values')
AnimationChannel = namedtuple('AnimationChannel', 'sampler node path')
Animation        = namedtuple('Animation', 'samplers channels duration')
Skin             = namedtuple('Skin', 'joints inverse_bind_matrices')


def mesh_to_trimesh(meshes):
	merged = []
	for m in meshes:
		V = np.array(m.vertices)
		F = group_by_N( np.array(m.triangles).flatten(), 3)
		tmesh = trimesh.Trimesh(vertices = V,faces = F)
		merged.append( tmesh )
	merged = trimesh.util.concatenate( merged)
	return merged

def get_dtype_cnt(accessor):
	dtype = None
	if   accessor.componentType == pygltflib.BYTE: 			dtype = np.int8
	elif accessor.componentType == pygltflib.UNSIGNED_BYTE:	dtype = np.uint8
	elif accessor.componentType == pygltflib.SHORT:			dtype = np.int16
	elif accessor.componentType == pygltflib.UNSIGNED_SHORT:dtype = np.uint16
	elif accessor.componentType == pygltflib.UNSIGNED_INT:	dtype = np.uint32
	elif accessor.componentType == pygltflib.FLOAT:			dtype = np.float32

	cnt = 0
	if   accessor.type == 'VEC4':		cnt = 4
	elif accessor.type == 'VEC3':	cnt = 3
	elif accessor.type == 'VEC2':	cnt = 2
	elif accessor.type == 'SCALAR':	cnt = 1

	return dtype, cnt


def load_accessor_data(gltf, accessor):
	buffer_view = gltf.bufferViews[accessor.bufferView]
	buffer = gltf.buffers[buffer_view.buffer]
	data = gltf.get_data_from_buffer_uri(buffer.uri)
	dtype, cnt = get_dtype_cnt(accessor)
	clipped_data = data[buffer_view.byteOffset : buffer_view.byteOffset + buffer_view.byteLength]
	elements = np.frombuffer(clipped_data, dtype=dtype)
	if cnt > 1:
		elements = np.reshape(elements, (-1, cnt))
	return elements

def order_nodes_root_first(nodes):
	'''
		Returns the nodes sorted so that the parents come first. This helps make transforming bone chain hierarchies trivial.
	'''
	parent_indexes = [-1] * len(nodes)
	for node in nodes:
		node.parent_index = -1
	for i, node in enumerate(nodes):
		for child_node_index in node.children:
			nodes[child_node_index].parent_index = i
	ordered_parent_indexes = {}
	for i in range(len(nodes)):
		def add_node(j):
			if j in ordered_parent_indexes:
				return
			parent_index = nodes[j].parent_index
			if parent_index >= 0:
				add_node(parent_index)
			ordered_parent_indexes[j] = 1
		add_node(i)
	return list(ordered_parent_indexes)


def load_model(fname):
	basedir = os.path.dirname(os.path.abspath(fname))

	gltf = pygltflib.GLTF2().load(fname)
	assert gltf is not None

	meshes = []
	for mesh in gltf.meshes:
		primitives = []
		assert mesh.primitives is not None
		for p in mesh.primitives:
			triangles = vertices  = normals = uvs = joints = weights = None

			assert p.indices is not None
			assert p.attributes.POSITION is not None

			vertices  = load_accessor_data(gltf, gltf.accessors[p.attributes.POSITION])
			triangles = load_accessor_data(gltf, gltf.accessors[p.indices])
			assert vertices is not None
			assert triangles is not None
			assert vertices.dtype == np.float32
			assert np.max(triangles) == len(vertices) - 1

			if p.attributes.NORMAL is not None:
				normals   = load_accessor_data(gltf, gltf.accessors[p.attributes.NORMAL])
				assert normals.dtype == np.float32

			if p.attributes.TEXCOORD_0 is not None:
				uvs     = load_accessor_data(gltf, gltf.accessors[p.attributes.TEXCOORD_0])
				assert uvs.dtype == np.float32

			if p.attributes.JOINTS_0 is not None:
				joints  = load_accessor_data(gltf, gltf.accessors[p.attributes.JOINTS_0])

			if p.attributes.WEIGHTS_0 is not None:
				weights = load_accessor_data(gltf, gltf.accessors[p.attributes.WEIGHTS_0])

			if normals is not None and uvs is not None:
				assert len(vertices) == len(normals) == len(uvs)

			if joints  is not None and weights is not None :
				assert joints.dtype in (np.uint8, np.uint16, np.uint32)
				assert weights.dtype == np.float32
				assert len(vertices) == len(joints) == len(weights)
				joints = np.array(joints, dtype=np.uint16)

			primitives.append(gltfPrimitive(mesh.name, p.material, triangles, vertices, normals, uvs, joints, weights))
		meshes.append(gltfMesh(mesh.name, primitives))

	#prepare texture file loading
	texture_info = []
	for ti in gltf.images:
		assert ti.uri
		name,ext = os.path.splitext(ti.uri)
		texture_info.append( TextureInfo(basedir, 0, None, ti.mimeType, ti.name, ti.uri) ) #dir bufferViewID gltfBufferView mimeType name uri

	animations = []
	skins = []
	for anim in gltf.animations:
		samplers = []
		channels = []
		duration = 0
		for sampler in anim.samplers:
			keyframe_times  = load_accessor_data(gltf, gltf.accessors[sampler.input])
			keyframe_values = load_accessor_data(gltf, gltf.accessors[sampler.output])
			samplers.append(AnimationSampler(sampler.interpolation, keyframe_times, keyframe_values) )
			if keyframe_times[-1] > duration:
				duration = keyframe_times[-1]

		for chnl in anim.channels:
			channels.append(AnimationChannel(chnl.sampler, chnl.target.node, chnl.target.path))

		animations.append( Animation(samplers, channels, duration) )

		for skin in gltf.skins:
			joints = skin.joints # invariant through pose?
			if skin.inverseBindMatrices is not None:
				inverse_bind_matrices = load_accessor_data(gltf, gltf.accessors[skin.inverseBindMatrices])
				inverse_bind_matrices = inverse_bind_matrices.reshape((-1, 16))
				assert inverse_bind_matrices.dtype == np.float32
				skins.append(Skin(joints, inverse_bind_matrices))

	ordered_node_indexes = order_nodes_root_first(gltf.nodes)
	name = Path(fname).stem
	return gltfModel(name, gltf.nodes, ordered_node_indexes, meshes, animations, skins, texture_info)

