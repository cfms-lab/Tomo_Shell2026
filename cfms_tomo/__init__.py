import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# TomoNV example, C++ Dll version
from cfms_meshcut.cut_group import CutGroup
from .tomo_slicingOptions import SlicingOptions
from .tomo_dll_interface import TomoDLLInterface

g_bVerbose = True
g_bUseCUDA = False
g_bShellMesh = True
g_tomo_theta_YP = 10


class  TomoManager:#manage C++ DLL and MeshTomo objects
	def __init__(self, s_o : SlicingOptions):
		self.slicing_option = s_o
		self.CppDLL =  TomoDLLInterface(
      		"Tomo_Shell2026.dll",		#DLL filename
			s_o,						#3D printer slicing options
			s_o.bUseCUDA,
			s_o.bShellMesh)	#default: True. The input data is not closed

	def get_best_orientation(self, C_G: CutGroup):
		self.name = f"{C_G.name}_tomo"
		self.input_gr = C_G
		for c_o in C_G.cutobjects:
			c_o.tomo_object = self.CppDLL.run_dll( c_o, self.slicing_option.bVerbose)

	def	get_shells(self, offset_size):
		C_G = self.input_gr
		unrotated = C_G.get_shells(offset_size)
		rotated   = C_G.get_shells(offset_size)
		unrotated.name = f"{self.name}_unrotated"
		rotated.name   = f"{self.name}_rotated"

		for c_o in rotated.cutobjects:
				c_o.transform(c_o.tomo_object.mat4x4)

		return unrotated, rotated
