import numpy as np
import trimesh

def offset_trimesh(tmesh : trimesh.Trimesh, offset_size):
	V  		= np.array(tmesh.vertices, copy = True)
	F  		= np.array(tmesh.faces, copy = True)

	if abs(offset_size) < 1e-2:
		return trimesh.Trimesh(V,F)

	from meshlib import mrmeshpy, mrmeshnumpy
	# https://meshlib.io/feature/precision-mesh-offsetting-with-meshlib/
	ml_mesh = mrmeshnumpy.meshFromFacesVerts(F, V)
	params = mrmeshpy.OffsetParameters()
	params.voxelSize = 1.
	if mrmeshpy.findRightBoundary(ml_mesh.topology).empty():
		params.signDetectionMode = mrmeshpy.SignDetectionMode.HoleWindingRule  # use if you have holes in mesh
	#offset = .5
	ml_shell = mrmeshpy.offsetMesh( ml_mesh, offset_size, params)

	V1 = mrmeshnumpy.getNumpyVerts(ml_shell)
	F1 = mrmeshnumpy.getNumpyFaces(ml_shell.topology)

	return trimesh.Trimesh(V1,F1)
