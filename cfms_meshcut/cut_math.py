import numpy as np
import trimesh

ps_white = np.array( [255,255,255])

def normalize(x):
	n = np.linalg.norm(x)
	return x / n if n > 1e-12 else np.asarray(x, dtype=float)

def pt_to_plane_dist(point, plane_point, plane_normal):
    vec = np.subtract(point, plane_point).flatten()
    vec = normalize(vec)
    return np.dot( plane_normal, vec)


def append_bbox(bbox1,bbox2):
	bmin = bbox1[0]
	bmax = bbox1[1]
	bmin = np.min( np.column_stack((bmin,bbox2[0])).T , axis=0)
	bmax = np.max( np.column_stack((bmax,bbox2[1])).T , axis=0)
	return np.column_stack((bmin,bmax)).T

def point_to_bone_dist( point6f, bone6f):
	#[ORIGINAL METHOD - kept as-is for before/after comparison] cutType.bone_p2bdist
	#https://math.stackexchange.com/questions/322831/determing-the-distance-from-a-line-segment-to-a-point-in-3-space
	q  = np.array(point6f[0:3]) #reference vertex (or triangle center)
	qn = np.array(point6f[3:6]) #vertex normal (or triangle normal)
	p1 = np.array(bone6f[0:3]) #bone_tip
	p2 = np.array(bone6f[3:6]) #the other tip
	u  = np.subtract( p2, p1).flatten()
	v  = np.subtract(  q, p1).flatten()
	u_norm = np.linalg.norm( u)
	uv_dot = np.dot( u, v)
	criteria = uv_dot
	if np.abs(u_norm) > 1e-5:  criteria = uv_dot / (u_norm * u_norm)

	signed_dist1 = pt_to_plane_dist( p1, q, qn)
	signed_dist2 = pt_to_plane_dist( p2, q, qn)
	if all([signed_dist1 > 1e-3,signed_dist2 > 1e-3]):
		return max(signed_dist1, signed_dist2)*1e3

	if criteria > 1.:
		return np.linalg.norm( np.subtract( p2, q))
	elif criteria < 1e-5:
		return np.linalg.norm( np.subtract( p1, q))
	#else:# [0,1] interval
	p = p1 + (uv_dot / u_norm / u_norm) *u
	return np.linalg.norm( np.subtract(  p, q))


def point_to_bone_dist_v2( point6f, bone6f, normal_weight=2.0):
	#[NEW METHOD - improved] cutType.bone_p2bdist2
	#Distance from a surface point (with its outward normal) to a bone segment p1-p2.
	#The original point_to_bone_dist() applies a BINARY penalty (x1e3) whenever both bone
	#tips lie on the +normal side, using a hard cosine threshold (1e-3). That discontinuity
	#makes adjacent triangles with slightly different normals jump to different bones -> the
	#noisy, fragmented body parts reported in the paper (e.g. M20/87k hip not detected).
	#Here the penalty is a CONTINUOUS factor of the surface-to-segment distance, so
	#neighbouring elements vary smoothly and stay connected.
	q  = np.asarray(point6f[0:3], dtype=float) #reference vertex (or triangle center)
	qn = np.asarray(point6f[3:6], dtype=float) #vertex normal (or triangle normal)
	p1 = np.asarray(bone6f[0:3], dtype=float)  #bone_tip
	p2 = np.asarray(bone6f[3:6], dtype=float)  #the other tip
	u  = p2 - p1
	v  = q  - p1
	uu = np.dot( u, u)
	t  = np.dot( u, v) / uu if uu > 1e-12 else 0.0
	t  = min( 1.0, max( 0.0, t))            #clamp the projection onto the segment [p1,p2]
	closest = p1 + t * u
	d  = np.linalg.norm( q - closest)       #geometric point-to-segment distance

	#normal consistency: for a watertight body the bone must lie on the INWARD (~ -qn) side.
	to_bone = closest - q
	n = np.linalg.norm( to_bone)
	align = np.dot( qn, to_bone) / n if n > 1e-9 else 0.0  # +1: bone is outward (wrong side), -1: inward (good)
	return d * (1.0 + normal_weight * max( 0.0, align))


def smooth_vertex_labels(labels, tmesh, iterations=3):
	#Mesh-connectivity label smoothing: iterative neighbour-majority vote over the mesh graph.
	#Removes isolated mislabelled vertices (the disconnected/fragmented body parts reported in
	#the paper) regardless of the underlying distance metric. Used by cutType.bone_p2bdist3.
	labels = np.asarray(labels).copy()
	neighbors = tmesh.vertex_neighbors #list (per vertex) of adjacent vertex indices
	for _ in range(iterations):
		new_labels = labels.copy()
		for vi, nb in enumerate(neighbors):
			if len(nb) == 0: continue
			votes = np.append(labels[np.asarray(nb, dtype=int)], labels[vi]) #include self
			new_labels[vi] = np.bincount(votes).argmax()
		labels = new_labels
	return labels


def rescale(vertices, max_height, RxRyRz=(0., 0., 0.)):#avatar 키가 max_height가 되도록 self.과 joints를 확대시킨다. (RxRyRz was an undefined global -> now a parameter)
	m_min = np.ones(3) * 1e5
	m_max = np.ones(3) * -1e5
	p_min = np.min( vertices,axis=0)
	p_max = np.max( vertices,axis=0)
	m_min = np.min( np.array([p_min, m_min]), axis=0)
	m_max = np.max( np.array([p_max, m_max]), axis=0)

	vec1 = m_min * -1
	D1 = np.eye(4)
	D1[0:3,3] = m_min * -1

	R = trimesh.transformations.euler_matrix(
		RxRyRz[0],
		RxRyRz[1],
		RxRyRz[2], 'syxz')

	finalM = R @ D1
	finalM[:3, :3] *= max_height# / (m_max[2] - m_min[2])

	new_vtx = np.c_[ vertices, np.ones(len(vertices))]
	new_vtx = np.dot(finalM, new_vtx.T).T
	return new_vtx[:,0:3]

