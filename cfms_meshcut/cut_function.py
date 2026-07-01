from enum import Enum, auto
from collections import namedtuple
import time
import datetime


class cutType(Enum):
    no_cut 		= auto()

    kmeans 		= auto()
    kmeans2 	= auto()
    aggler 		= auto()
    DBSCAN	 	= auto()
    KMedoids 	= auto()
    spectral	= auto()

    bone_kmeans 	= auto()
    bone_KMedoids = auto()
    bone_pairdist = auto()
    bone_p2bdist 	= auto()#original point-to-bone distance
    bone_p2bdist2 = auto()#improved point-to-bone distance (continuous normal penalty)
    bone_p2bdist3 = auto()#improved + mesh-connectivity label smoothing (handled in CutManager)
    bone_skinweight = auto()#rig skin-weight based segmentation (handled in CutManager)

CutOption  = namedtuple('CutOption', 'name type number')

def cutFunction(cut_option : CutOption, V, Fc, Vn, Fn, bonetip1, bonetip2):
	groups = centroids = []
	bPerVertex = True
	Tp 	= cut_option.type.value
	No 	= cut_option.number

	if Tp == cutType.kmeans.value:#raw data
		from trimesh.points import k_means
		(centroids, groups) = k_means( Fc, No)#trimesh.points.k_means
		bPerVertex = True

	elif Tp == cutType.kmeans2.value:#방법2
		from scipy.cluster.vq import kmeans2
		(centroids, groups) = kmeans2(V, No) #scipy.cluster.vq.kmeans
		bPerVertex = False

	elif Tp == cutType.aggler.value:#bVertex로 해야 됨.
		from sklearn.cluster import AgglomerativeClustering
		import networkx as nx
		from sklearn.neighbors import kneighbors_graph
		agg_clustering = AgglomerativeClustering(n_clusters=No, metric='euclidean', linkage='ward',connectivity=None)
		groups = agg_clustering.fit_predict(V)

	elif Tp == cutType.DBSCAN.value:
		from sklearn.cluster import DBSCAN
		result = DBSCAN(eps=No, min_samples=5).fit(V)
		groups = result.labels_

	elif Tp == cutType.KMedoids.value:#kMedoids
		from sklearn_extra.cluster import KMedoids
		km = KMedoids(n_clusters=No,metric="manhattan", random_state=0, max_iter = 300).fit(V)
		groups, centroids = km.labels_, km.cluster_centers_

	elif Tp == cutType.spectral.value:
		from sklearn.cluster import SpectralClustering
		result = SpectralClustering(
    		n_clusters=6,
				n_components = 6,
      	assign_labels='discretize',
				eigen_solver = 'amg',
				eigen_tol = 'auto',
				affinity = 'nearest_neighbors',
        random_state=0).fit(V)
		groups = result.labels_

	#---------bone-based
	elif Tp == cutType.bone_kmeans.value:
		from sklearn.cluster import KMeans
		result = KMeans(n_clusters= len(bonetip1), init=bonetip1, n_init=1)
		result.fit(V)
		(groups, centroids) = (result.labels_, result.cluster_centers_)

	elif Tp == cutType.bone_KMedoids.value:
		from sklearn_extra.cluster import KMedoids
		import numpy as np
		km = KMedoids(
    	n_clusters=6,
     	metric="manhattan",
      method = 'pam',
      random_state=0,
      max_iter = 100
      ).fit(V)
		groups, centroids = km.labels_, km.cluster_centers_


	elif Tp == cutType.bone_pairdist.value:#k-Medoids, fixed centroid. 제일 잘 되지만 오른 팔목 그룹 오류.
		#https.value://www.google.com/search?q=python+K-Medoids+for+fixed+centroids&sca_esv=440a43a3eb6979b0&sxsrf=AE3TifOSEHY3wAGCU-YTO-evFzh9k5m_7g%3A1752401570371&ei=ooZzaI61FtDP2roPu7X2yQ0&ved=0ahUKEwiOjuzIzLmOAxXQp1YBHbuaPdkQ4dUDCBA&uact=5&oq=python+K-Medoids+for+fixed+centroids&gs_lp=Egxnd3Mtd2l6LXNlcnAiJHB5dGhvbiBLLU1lZG9pZHMgZm9yIGZpeGVkIGNlbnRyb2lkczIFECEYoAEyBRAhGKABSJ0xUPILWLcvcAF4AJABAZgBlAOgAcImqgEIMi0yMC4wLjG4AQPIAQD4AQGYAhSgAvshwgIKEAAYsAMY1gQYR8ICBRAAGO8FwgIIEAAYogQYiQXCAgYQABgIGB7CAgcQIRigARgKwgIEECEYFZgDAIgGAZAGCpIHBjEuMC4xOaAHgUCyBwQyLTE5uAf2IcIHBDE1LjXIBxI&sclient=gws-wiz-serp
		from sklearn_extra.cluster import KMedoids
		from sklearn.metrics.pairwise import pairwise_distances
		import numpy as np
		distances = pairwise_distances(V, bonetip1)
		groups = np.argmin(distances, axis=1)

	elif Tp == cutType.bone_p2bdist.value:#K-medoids, bone과의 거리 기준.  관절을 따라기간 하지만 일부 그룹이 분리되어 있다.
		#https.value://www.google.com/search?q=scklearn+K-Medoids+user+defined+metric&sca_esv=e770264821b4b2f0&sxsrf=AE3TifOE53hwOVgrtzoV9ShG1IgsR_-Drg%3A1752407766763&ei=1p5zaOmVLsKq0-kP6PaZ-AM&ved=0ahUKEwjp2MHT47mOAxVC1TQHHWh7Bj8Q4dUDCBA&uact=5&oq=scklearn+K-Medoids+user+defined+metric&gs_lp=Egxnd3Mtd2l6LXNlcnAiJnNja2xlYXJuIEstTWVkb2lkcyB1c2VyIGRlZmluZWQgbWV0cmljMgUQABjvBTIIEAAYgAQYogQyCBAAGIAEGKIEMgUQABjvBTIIEAAYgAQYogRIpB9QogdY8RZwAXgBkAEAmAHuAqABoROqAQUyLTkuMbgBA8gBAPgBAZgCBaACswfCAgoQABiwAxjWBBhHwgIKECEYoAEYwwQYCpgDAOIDBRIBMSBAiAYBkAYKkgcFMS4wLjSgB6grsgcDMi00uAevB8IHBTEuMy4xyAcH&sclient=gws-wiz-serp
		import numpy as np
		from sklearn.metrics.pairwise import pairwise_distances
		from cfms_meshcut.cut_math import point_to_bone_dist
		point6f 	= np.concatenate((V, Vn), axis=1)
		bone6f 		= np.concatenate((bonetip1, bonetip2), axis=1)
		distances = pairwise_distances(point6f, bone6f, metric=point_to_bone_dist)
		groups 		= np.argmin(distances, axis=1)

	elif Tp in (cutType.bone_p2bdist2.value, cutType.bone_p2bdist3.value):#improved point-to-bone distance (continuous normal penalty). bone_p2bdist3 adds connectivity smoothing in CutManager.
		import numpy as np
		from sklearn.metrics.pairwise import pairwise_distances
		from cfms_meshcut.cut_math import point_to_bone_dist_v2
		point6f 	= np.concatenate((V, Vn), axis=1)
		bone6f 		= np.concatenate((bonetip1, bonetip2), axis=1)
		distances = pairwise_distances(point6f, bone6f, metric=point_to_bone_dist_v2)
		groups 		= np.argmin(distances, axis=1)

	return (groups, bPerVertex)

def StartTimer(str=""):
  if len(str)>0:
    print(str)
  return time.time()

def EndTimer( start_time, filename):
	end_time = time.time();    total_time = end_time - start_time
	print(filename + '= ', datetime.timedelta(seconds=total_time), ' seconds \n')
