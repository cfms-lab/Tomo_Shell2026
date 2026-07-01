import numpy as np
from collections import namedtuple
from typing import Optional
from cfms_tomo.tomo_io import FStr

VolMassData = namedtuple( 'VolMassData', 'yaw pitch roll Mo Mss Mtotal' )

class TomoResult:
	vmData = VolMassData( 0, 0, 0, 0, 0, 0 )

	def __init__(self, yprm6f = None):
		if yprm6f is not None:
			self.vmData = VolMassData(
				yaw = yprm6f[0], pitch = yprm6f[1], roll   = yprm6f[2],
				Mo = yprm6f[3],  Mss   = yprm6f[4], Mtotal = yprm6f[5])
		self.mat4x4 = None #transform matrix

	def get_ypr_in_degree(self):
		return (
          self.vmData.yaw   * 180 / np.pi,
          self.vmData.pitch * 180 / np.pi,
          self.vmData.roll  * 180 / np.pi)

	def get_ypr_in_radian(self):
		return (
          self.vmData.yaw,
          self.vmData.pitch,
          self.vmData.roll )

	def set_max_length(self, tmesh):
		self.BeamLength = np.max( tmesh.bounding_box_oriented.extents, axis=0)

	def get_max_length(self):
		return self.BeamLength

	def GetMss(self):
		return self.vmData[4]

	def print(self):
		print(FStr(self.vmData))
