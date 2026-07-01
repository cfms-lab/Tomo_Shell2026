# %%
from  cfms_tomo.shell_test.tomoSh_io_trimesh import *

class tomoSh_Cpp:
  FileName = ""; mesh0 = [];vtx = []; tri=[]; vtx_nrm=[]; xx=[]; yy=[];zz=[];
  YPR=[];DLL_Info=[];CppFunction = [];Cdll_opt_id=[];CppDLL=[];
  Mo3D=[];Mss3D=[];Mtotal3D=[];AABB2D=(0,0,0,0);chull_vtx=[];tri_area=[]
  vm_info=[]

  wall_thickness = 1.0 # [mm]
  PLA_density    = 0.001121 # density of PLA filament, [g/mm^3] (= 1.121 g/cm^3, ASTM E1461 측정값)
  Fclad = 1.0 # fill ratio of cladding, always 1.0
  Fcore = 0.15 # fill ratio of core, (0~1.0)
  Fss   = 0.2 # fill ratio of support structure, (0~1.0)
  Css   = 1. # correction constant for Mss. obsolete. replaced by getWeightZSum[]
  Fclad = 1.
  bVerbose = False
  bUseExplicitSS = False
  bUseClosedVolumeVoxel = False
  bShellMesh = False
  ShellThickness = 0.5
  dVoxel = 1. #default: 1mm voxel
  nVoxel = 256 #default: 256 x 256 x 256 voxels
  theta_c = toRadian(60.)
  nYPR_Intervals = 0
  Vtc_mm = []
  BedType = (enumBedType.ebtRaft  , 0., 0., 0.)


  def __init__(self, filename, nYPR_Intervals, yaw_range, pitch_range, roll_range, bVerbose):
    self.FileName = filename
    (self.mesh0, self.tri, self.vtx, self.vtx_nrm, self.tri_nrm,  self.tri_area, self.tri_center, self.chull_tri, self.chull_vtx, self.chull_trinrm) = LoadInputMesh( filename)
    (self.xx,self.yy,self.zz)   = np.meshgrid( yaw_range, pitch_range, roll_range)
    self.YPR = np.column_stack([self.xx.ravel(), self.yy.ravel(), self.zz.ravel()]).astype(np.float32) #https://rfriend.tistory.com/352
    self.nYPR_Intervals = nYPR_Intervals
    self.bVerbose = bVerbose

    (mesh1_min, mesh1_max,_) = getBoundary( self.vtx)
    (x1,y1,z1) = list(map(int, mesh1_max))
    (x0,y0,z0) = list(map(int, mesh1_min))
    max_dimension = max(max( x1-x0, y1-y0), z1-z0)
    self.AABB2D = (0, 0, max_dimension, max_dimension)#for plot2D()

    if self.bVerbose:
      print('vtx=',self.vtx.shape)
      print('tri=',self.tri.shape)
      print('YPR=',toDegree(self.YPR), self.YPR.shape)

  def Run(self, cpp_function_name):
    global g_mesh0_surface_area,g_CppDLLFileName
    g_mesh0_surface_area = self.mesh0.area

    self.Float32Info = np.array([ # Do not change this order!!
      self.dVoxel,  self.theta_c,  g_mesh0_surface_area,  self.wall_thickness,
      self.Fcore, self.Fclad,   self.Fss, self.Css,
      self.PLA_density, self.BedType[1], self.BedType[2], self.BedType[3]]).astype( np.float32)

    self.Int32Info = np.array([   # Do not change this order!!
      self.bVerbose,      self.bUseExplicitSS,  self.bShellMesh,   self.nVoxel,
      self.tri.shape[0],  self.vtx.shape[0],    self.YPR.shape[0],
      self.chull_tri.shape[0],  self.chull_vtx.shape[0], self.BedType[0],
      int(round(self.ShellThickness * 1000.0))]).astype( np.int32)

    # if self.bVerbose:
    time0 = StartTimer()

    self.CppDLL =  ct.WinDLL(g_CppDLLFileName)
    self.CppFunction = getattr(self.CppDLL, cpp_function_name)
    self.CppFunction.argtypes   = (  Cptr1d, Cptr1iL,  Cptr1d, Cptr1iL, Cptr1d, Cptr1d, Cptr1d, Cptr1iL, Cptr1d, Cptr1d)
    self.CppFunction.restype    = ct.c_int32
    self.Cdll_opt_id = self.CppFunction(
        np_to_Cptr1d( self.Float32Info),
        np_to_Cptr1iL(self.Int32Info),
        np_to_Cptr1d( self.YPR),
        np_to_Cptr1iL(self.tri),
        np_to_Cptr1d( self.vtx),
        np_to_Cptr1d( self.vtx_nrm),
        np_to_Cptr1d( self.tri_nrm),
        np_to_Cptr1iL(self.chull_tri),
        np_to_Cptr1d( self.chull_vtx),
        np_to_Cptr1d( self.chull_trinrm)  )

    #if self.bVerbose:
    EndTimer( time0, self.FileName + '    ' + cpp_function_name)

    # (5) Retreive data from C++ dll
    self.CppDLL.getMo.argtypes  = (); self.CppDLL.getMo.restype  = Cptr1d
    self.CppDLL.getMss.argtypes = (); self.CppDLL.getMss.restype = Cptr1d

    self.Mo3D  = np.array(Cptr1d_to_np(self.CppDLL.getMo(),  self.YPR.shape[0])).astype(np.float32)
    self.Mss3D = np.array(Cptr1d_to_np(self.CppDLL.getMss(), self.YPR.shape[0])).astype(np.float32)
    self.Mtotal3D = self.Mo3D + self.Mss3D

    self.CppDLL.getVolMassInfo.argtypes = (); self.CppDLL.getVolMassInfo.restype = Cptr1d
    self.vm_info = np.array(Cptr1d_to_np(self.CppDLL.getVolMassInfo(),  21)).astype(np.float32)

    if(self.bVerbose):
      print( 'Mo3D=    ', FStr(self.Mo3D.reshape(     self.nYPR_Intervals,self.nYPR_Intervals) , precision=2))
      print( 'Mss3D=   ', FStr(self.Mss3D.reshape(    self.nYPR_Intervals,self.nYPR_Intervals) , precision=2))
      print( 'Mtotal3D=', FStr(self.Mtotal3D.reshape( self.nYPR_Intervals,self.nYPR_Intervals) , precision=2))
      # np.savetxt('Mo.txt',  Mo3D.reshape( self.nYPR_Intervals,self.nYPR_Intervals), delimiter='\t')
      # np.savetxt('Mss.txt', self.Mss3D.reshape(self.nYPR_Intervals,self.nYPR_Intervals), delimiter='\t')

    # (6) rendering
    #import this
    self.CppDLL.getnData2i.argtypes = ( ct.c_short,); self.CppDLL.getnData2i.restype = ct.c_int32
    self.CppDLL.getpData2i.argtypes = ( ct.c_short,); self.CppDLL.getpData2i.restype = Cptr1i

    if(self.bVerbose):
      for p_type, p_name in zip ( g_PixelEnums, g_PixelVarNames ):
        p_enum = getattr( enumPixelType, p_type).value
        n_2i = self.CppDLL.getnData2i( p_enum );   p_2i = self.CppDLL.getpData2i( p_enum )
        if n_2i == 0:
          setattr( self, p_name, np.array([[0,0,0,0,0,0]]) )
        else:
          setattr( self, p_name, Cptr1i_to_np( p_2i, n_2i*g_nPixelFormat).reshape(n_2i,g_nPixelFormat) )

    self.CppDLL.OnDestroy.argtype = (None,)
    self.CppDLL.OnDestroy.restype = None
    self.CppDLL.OnDestroy()


    # debug
  def Print_tabbed(self):
    if self.bVerbose:
      print("Va, Vb, Vtc, Vnv,")
      print( self.vm_info[0],
             self.vm_info[1],
             self.vm_info[2],
             self.vm_info[3], sep=" ")
      print("Vss, Vss_clad, Vss_core, Ass_clad,")
      print( self.vm_info[4],
             self.vm_info[5],
             self.vm_info[6],
             self.vm_info[7], sep=" ")
      print("Vo, Vo_clad, Vo_core,")
      print( self.vm_info[8],
             self.vm_info[9],
             self.vm_info[10], sep=" ")
      print("Vbed, Mbed,")
      print( self.vm_info[11],
             self.vm_info[12], sep=" ")
      print("Mss, Mss_clad, Mss_core,")
      print( self.vm_info[13],
             self.vm_info[14],
             self.vm_info[15], sep=" ")
      print("Mo, Mo_clad, Mo_core,")
      print( self.vm_info[16],
             self.vm_info[17],
             self.vm_info[18], sep=" ")
      print("Mtotal, SS_vol,")
      print( self.vm_info[19],
             self.vm_info[20], sep=" ")

  def Print_table(self):
    if self.bVerbose:
      vm_info_str = ('Va', ' Vb', ' Vtc', ' Vnv', ' Vss', ' Vss_clad', ' Vss_core', ' Ass_clad', ' Vo', ' Vo_clad', ' Vo_core', ' Vbed', ' Mbed', ' Mss', ' Mss_clad', ' Mss_core', ' Mo', ' Mo_clad', ' Mo_core', ' Mtotal')
      for v, vm_info in enumerate(vm_info_str):
        print(self.vm_info[v])
        #print(vm_info, self.vm_info[v])
