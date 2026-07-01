import numpy as np
import trimesh

def group_by_N(data, N):
  #  주어진 리스트를 N개씩 묶어 2차원 리스트로 반환합니다.
  return [data[i:i + N] for i in range(0, len(data), N)]

class hfMesh:
	def __init__(self, renderer, name, _mesh, tex_data):
		self.renderer 	= renderer
		self.name 		= name
		self.mesh 		= _mesh
		self.tex_data 	= tex_data
		self.is_shared 	= False

		self.instance_data = None
		self.max_instances = 512
		self.prepared_instances = 0

	def to_trimesh(self):
		#prepare trimesh object for k-means clustering
		return hfmesh_to_trimesh(self.mesh)

	def add_to(self, ps):
		M = self.mesh
		faces = group_by_N( np.array(M.triangles).flatten(), 3)
		ps_mesh = ps.register_surface_mesh(
						name 		= self.name,#name = 빼면 안됨
						vertices 	= M.vertices,
						faces 		= faces,
						color 		= np.ones(3)
					)
		if hasattr(self, 'tex_data'):
			if self.tex_data is not None:
				if len(self.tex_data)>0:
					uv_name = f"{self.name}_uv"
					ps_mesh.add_parameterization_quantity(
								name 		= uv_name,
								values		= M.uvs
							)
					ps_mesh.add_color_quantity(
								f"{self.name}_tex",
								self.tex_data,
								defined_on	= 'texture',
								param_name	= uv_name,
								image_origin='lower_left',
								enabled		= True
							)
		return ps_mesh

	def get_bounds(self):
		m_min = np.ones(3) * 1e5
		m_max = np.ones(3) * -1e5
		for v in self.mesh.vertices:
			m_min = np.min( np.array([v, m_min]), axis=0)
			m_max = np.max( np.array([v, m_max]), axis=0)

		self.bounds = np.array([m_min, m_max])
		return self.bounds


def hfmesh_to_trimesh(M : hfMesh):
	tmesh = trimesh.Trimesh(
				vertices 		= M.vertices,
				faces 			= group_by_N( np.array(M.triangles).flatten(), 3),
				vertex_normals 	= M.normals
			)
	tmesh.visual = trimesh.visual.texture.TextureVisuals( uv = M.uvs)
	return tmesh

def merge_hfmeshes_to_a_trimesh(meshes):
	merged = []
	for m in meshes:
		merged.append( m.to_trimesh() )
	merged = trimesh.util.concatenate( merged)
	return merged
