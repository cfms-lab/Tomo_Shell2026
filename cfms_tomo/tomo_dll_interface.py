import os
import numpy as np
import ctypes as ct
from copy import copy, deepcopy
from typing import Optional

from cfms_meshcut.cut_object import *
from cfms_tomo.tomo_io import *
from cfms_tomo.tomo_object import *
from cfms_tomo.tomo_slicingOptions import *

class TomoDLLInterface:
	CppDLL = None
	slicing_option = None

	#interval variables. for search
	nYPR_Intervals = 1
	(yaw_range, pitch_range, roll_range) = ([],[],[])#search range
	(xx,yy,zz, YPR) = ([],[],[],[])
	(Float32Info, Int32Info) = ([], [])
	(bUseExplicitSS,bUseClosedVolumeVoxel) = (True,False) #obsolete.

	def __init__(self, dll_fname,  s_o : Optional[SlicingOptions], bUseCUDA, bShellMesh):
		self.CppDLL =  ct.WinDLL( os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_fname )
		self.CppFunction = getattr(self.CppDLL, 'TomoSh_CUDA' if bUseCUDA else 'TomoSh_INT3')
		self.CppFunction.argtypes   =(  Cptr1d, Cptr1iL,  Cptr1d, Cptr1iL, Cptr1d, Cptr1d, Cptr1d, Cptr1iL, Cptr1d, Cptr1d)
		self.CppFunction.restype    = ct.c_int32
		self.bShellMesh = bShellMesh

		L = self.CppDLL
		L.getMo.argtypes  = (); L.getMo.restype  = Cptr1d
		L.getMss.argtypes = (); L.getMss.restype = Cptr1d
		L.getMat4x4.argtypes = (); L.getMat4x4.restype = Cptr1d
		L.getnData2i.argtypes = ( ct.c_short,); L.getnData2i.restype = ct.c_int32
		L.getpData2i.argtypes = ( ct.c_short,); L.getpData2i.restype = Cptr1i

		S_O = self.slicing_option = copy(s_o)
		self.nYPR_Intervals= int(360 / S_O.theta_YP) +1
		self.yaw_range   = np.linspace(toRadian(0), toRadian(360), num=self.nYPR_Intervals, endpoint=True, dtype=np.float32)
		self.pitch_range = np.linspace(toRadian(0), toRadian(360), num=self.nYPR_Intervals, endpoint=True, dtype=np.float32)
		self.roll_range  = np.zeros(1)
		(self.xx,self.yy,self.zz)   = np.meshgrid( self.yaw_range, self.pitch_range, self.roll_range)
		self.YPR = np.column_stack([self.xx.ravel(), self.yy.ravel(), self.zz.ravel()]).astype(np.float32) #https://rfriend.tistory.com/352


	def __del__(self):
		self.free()

	def free(self):
		self.CppDLL.OnDestroy.argtype = (None,)
		self.CppDLL.OnDestroy.restype = None
		self.CppDLL.OnDestroy()


	def run_dll( self, cutobject0, bVerbose):
		if bVerbose: print('Tomo processing: ', cutobject0.name)

		c_o = deepcopy(cutobject0)
		self.bShellMesh = self.slicing_option.bShellMesh and (not c_o.tmesh.is_watertight)

		T = c_o.tmesh
		vtx   			= np.asarray( T.vertices).astype(np.float32, copy = True) # 'TOMO_FLOAT32' type of C++ Dll.
		vtx_nrm   	= np.asarray( T.vertex_normals).astype(np.float32, copy = True)
		tri   			= np.asarray( T.faces).astype(np.int32, copy = True)  # 'MESH_ELE_ID_TYPE' type of C++ Dll.
		tri_nrm   	= np.asarray( T.face_normals).astype(np.float32, copy = True) # 'TOMO_FLOAT32' type of C++ Dll.

		H = T.convex_hull
		H_vtx 			= np.asarray( H.vertices).astype(np.float32, copy = True)
		H_tri   		= np.asarray( H.triangles).astype(np.int32, copy = True)  # 'MESH_ELE_ID_TYPE' type of C++ Dll.
		H_trinrm    = np.asarray( H.face_normals).astype(np.float32, copy = True) # 'TOMO_FLOAT32' type of C++ Dll.

		S_O = self.slicing_option
		self.Float32Info = np.array([ # Do not change this order!!
		S_O.dVoxel,  	 S_O.theta_c,  	T.area,  		S_O.wall_thickness,
		S_O.Fcore, 		 S_O.Fclad,   	S_O.Fss, 		S_O.Css,
		S_O.PLA_density, S_O.BedType[1],S_O.BedType[2], S_O.BedType[3]]).astype( np.float32)

		self.Int32Info = np.array([# Do not change this order!!
			bVerbose,  self.bUseExplicitSS,  self.bShellMesh,   S_O.nVoxel,
			tri.shape[0],  	vtx.shape[0],   self.YPR.shape[0],
			H_tri.shape[0], H_vtx.shape[0], S_O.BedType[0],
			int(round(S_O.ShellThickness * 1000.0))]).astype( np.int32)


		self.Cdll_opt_id = self.CppFunction(
			np_to_Cptr1d( self.Float32Info),
			np_to_Cptr1iL(self.Int32Info),
			np_to_Cptr1d( self.YPR),
			np_to_Cptr1iL(tri),
			np_to_Cptr1d( vtx),
			np_to_Cptr1d( vtx_nrm),
			np_to_Cptr1d( tri_nrm),
			np_to_Cptr1iL(H_tri),
			np_to_Cptr1d( H_vtx),
			np_to_Cptr1d( H_trinrm)  )

		L = self.CppDLL
		t_o = TomoObject(c_o)#create class object

		#filament masses for (yaw, pitch, 0)
		Mss3D = np.array(Cptr1d_to_np(L.getMss(), self.YPR.shape[0])).astype(np.float32, copy = True)
		if os.environ.get("TOMO_DEBUG_MSS", "0").lower() in ("1", "true", "yes", "on"):
			best_ids = np.argsort(Mss3D)[:8]
			print(
				"TOMO_DEBUG_MSS",
				"min", float(np.min(Mss3D)),
				"max", float(np.max(Mss3D)),
				"sum", float(np.sum(Mss3D)),
				"best_ids", best_ids.tolist(),
				"best_vals", [float(Mss3D[i]) for i in best_ids],
			)
		if os.environ.get("TOMO_DEBUG_MSS_FULL", "0").lower() in ("1", "true", "yes", "on"):
			print("TOMO_DEBUG_MSS_FULL", [float(v) for v in Mss3D])

		#best/worst orientation
		(t_o.best_vminfo, _) = findOptimals(self.YPR, Mss3D, bVerbose)
		t_o.best_vminfo.set_max_length( T)#find OBB length

		#if bVerbose:
		#	print('Mss=', FStr(Mss3D), '\nbest=') #debug
		#	t_o.best.print()

		#bed/support voxels (for rendering)
		for p_type in (enumPixelType.eptSS, enumPixelType.eptBed):
			p_name = TOMO_PixelVarNames[p_type]
			n_2i = L.getnData2i( p_type )
			if n_2i > 0:
				p_2i = L.getpData2i( p_type )
				pxls = Cptr1i_to_np( p_2i, n_2i*TOMO_nPixelFormat).reshape(n_2i,TOMO_nPixelFormat)
				pxls = np.array(pxls).astype(float)[:,0:3] #C++ 내부에서는 int 6개로 사용. float 3개로 변환.
				t_o.pxl_groups.append( TomoPixels( p_type, p_name, pxls))

		t_o.mat4x4 = np.array(Cptr1d_to_np(L.getMat4x4(), 4*4)).astype(np.float32, copy = True).reshape(4, 4)

		return t_o
