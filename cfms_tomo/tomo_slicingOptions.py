import numpy as np
from tomo_io import toRadian
from enum import Enum

class enumPixelType(int, Enum):
  eptAl   = 0
  eptBe   = 1
  eptSSB  = 2
  eptSSA  = 3
  eptSS   = 4
  eptBed  = 5
  eptVo   = 6
  eptVss  = 7
  eptTC   = 8
  eptNVB  = 9
  eptNVA  = 10
  eptNumberOfSubPixels = 11

class enumBedType(int, Enum):
  ebtNone = 0,
  ebtBrim = 1,
  ebtRaft = 2,
  ebtSkirt = 3

#constants
g_tomo_theta_YP = 10
TOMO_nOptimalsToDisplay = 3 # number of optimal orientation to print
TOMO_nPixelFormat = 6 # pX, pY, pZ, nX, nY, nZ
TOMO_PixelVarNames  = ('al_pxls', 'be_pxls','SSB_pxls', 'SSA_pxls', 'SS_pxls','Bed_pxls','Vo_pxls','Vss_pxls','TC_pxls',   'NVB_pxls', 'NVA_pxls' )

class TomoPixels:
    def __init__(self,
            type : enumPixelType, name, pxls):
        self.type = type
        self.name = name
        self.pxls = pxls.copy()

    def copy(self):
        return TomoPixels( self.type, self.name, self.pxls)

class SlicingOptions:
	wall_thickness = 0.8 # [mm]
	PLA_density    = 0.001121 # density of PLA filament, [g/mm^3] (= 1.121 g/cm^3, ASTM E1461 측정값)
	Fclad   = 1.0 # fill ratio of cladding, always 1.0
	Fcore   = 0.15 # fill ratio of core, (0~1.0)
	Fss     = 0.2 # fill ratio of support structure, (0~1.0)
	Css     = 1.0 # correction constant for filament dilation effect.
	dVoxel  = 1.0 # size of voxel. Do not change this value.
	nVoxel  = 256 # number of voxels. Do not change this value.
	theta_c = toRadian(60.) #filament critical angle for support structure
	bUseExplicitSS = False #항상 True로 할 것.
	BedType = ( enumBedType.ebtRaft, 0, 2, 0.3 + 0.27 + 2 * 0.2)# 0, 래프트 크기(mm), 베이스 두께 + 인터페이스 두께  + 서피스 레이어 수 * 서피스 레이어 두께
	(Yaw, Pitch, Roll) = (0,0,0) # initial oritentation
	theta_YP = g_tomo_theta_YP #degree
	bVerbose = True
	bUseCUDA = True
	bShellMesh = True
	ShellThickness = 0.5
