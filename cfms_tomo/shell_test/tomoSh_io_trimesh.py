#---------------------------------------------------------
#global variables
from asyncio.windows_events import NULL
#from sklearn.metrics import adjusted_mutual_info_score

g_PlotResolution = 24 #quality of matplotlib scatter plot
g_bUseRAY = False
g_bUseSlotPairing = True
g_bUseExplicitSS = False
g_nCPU = 1
g_AABB2D = (0,0,0,0)
g_input_mesh_filename = ""


g_Cdll = NULL; g_CppDLLFileName = 'cfms_tomo\\Tomo_Shell2026.dll'
g_mesh0_min =0; g_mesh0_max =0; g_mesh0_center = (0,0,0); g_mesh0_surface_area = 0

g_PixelEnums     = (  'eptAl',      'eptBe',  'eptSSB',   'eptSSA',   'eptSS',  'eptBed',  'eptVo', 'eptVss',   'eptTC',     'eptNVB',   'eptNVA'  )
g_PixelTitles     = (     'α',          'β',    'SS_β',     'SS_α',      'SS',     'Bed',    'ΣVo',   'ΣVss',      'TC',       'NV_β',     'NV_α'     )
g_PixelColors    = (   'green',  'purple',     'lime',   'purple',     'red',    'blue',   'gray',    'red',     'red', 'sandybrown',    'aqua') #https://community.plotly.com/t/plotly-colours-list/11730/2
g_PixelVarNames  = ('al_pxls',    'be_pxls','SSB_pxls', 'SSA_pxls', 'SS_pxls','Bed_pxls','Vo_pxls','Vss_pxls','TC_pxls',   'NVB_pxls', 'NVA_pxls' )
g_PixelVisible  = (     True,      True,       False,      False,        True,    True,    False,     False,     False,       False,    False)
al_pxls=[]; be_pxls=[];  NVB_pxls=[]; NVA_pxls=[]; Vss_pxls=[]; TC_pxls=[]; Vo_pxls=[]; SS_pxls=[]; SSB_pxls=[]; SSA_pxls = []; Bed_pxls = []

#constants
g_fMARGIN     = 0.001 #prevent floating point round off error
g_fNORMALFACTOR = 1000.
g_nOptimalsToDisplay = 3 # number of optimal orientation to print
g_nPixelFormat = 6 # pX, pY, pZ, nX, nY, nZ

(origin, xaxis, yaxis, zaxis) = ([0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1])
g_voxel_size  = 1. #do not change this value
g_HALF_VOXEL_SIZE = g_voxel_size * 0.5

alpha_color = ([0.5, 0., 1.]) #violet
beta_color  = ([0., 0., 1.]) #blue
TC_color    = ([0., 1., 0.]) #green
NV_color    = ([1., 165./255., 0.]) #orange or magenta
SS_color    = ([1., 0., 0.]) #red
Vo_color    = ([0.5, 0.5, 0.5]) #gray

#---------------------------------------------------------
# interface to Cpp Dll (ctypes)

import numpy as np
import ctypes as ct

Cptr1i  = ct.POINTER(ct.c_short)#16bit
Cptr1iL  = ct.POINTER(ct.c_long)#32bit. for element IDs'
Cptr1d  = ct.POINTER(ct.c_float)#32bit

def np_to_Cptr1i( X):
	return X.ctypes.data_as(Cptr1i)

def np_to_Cptr1iL( X):
	return X.ctypes.data_as(Cptr1iL)

def np_to_Cptr1d( X):
	return X.ctypes.data_as(Cptr1d)

def Cptr1i_to_np(ptr, rows):
	if rows == 0:
		return []
	return np.array(ptr[:rows]).astype(np.int16)

def Cptr1iL_to_np(ptr, rows):
	if rows == 0:
		return []
	return np.array(ptr[:rows]).astype(np.int32)

def Cptr1d_to_np(ptr, rows):
	if rows == 0:
		return []
	return np.array(ptr[:rows]).astype(np.float32)

from enum import Enum, unique
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

#--------------------------------------------------------------
#strings
def my_FStr(float_value, precision=1):
	return "{0:.{precision}f}".format(float_value, precision=precision)
def my_toRadian(degree):
	return degree * np.pi / 180.
def my_toDegree(radian):
	return radian * 180. / np.pi

FStr     = np.vectorize( my_FStr)
toRadian = np.vectorize( my_toRadian)
toDegree = np.vectorize( my_toDegree)
#--------------------------------------------------------------
import time
import datetime
def StartTimer():
	return time.time()

def EndTimer( start_time, filename):
	end_time = time.time();    total_time = end_time - start_time
	print(filename + '= ', datetime.timedelta(seconds=total_time), ' seconds \n')

#--------------------------------------------------------------
#com. geom.
def getBoundary(vtx): #find AABB of Numpy np.asarray() data of  [x,y,z]
	v0_np = np.asarray( vtx)
	mesh0_min = np.array([np.min( v0_np[:,0]), np.min( v0_np[:,1]), np.min( v0_np[:,2])])
	mesh0_max = np.array([np.max( v0_np[:,0]), np.max( v0_np[:,1]), np.max( v0_np[:,2])])
	mesh0_center = (mesh0_min + mesh0_max) * 0.5
	return (mesh0_min,mesh0_max,mesh0_center)

def toCartesian( tht, phi, R):#yaw, pitch, R
	X = R * np.sin(tht) * np.cos(phi) # https://en.wikipedia.org/wiki/Spherical_coordinate_system
	Y = R * np.sin(tht) * np.sin(phi)
	Z = R * np.cos(tht)
	return(X,Y,Z)

from numpy import linalg as LA
def Area3D( p1, p2, p3):
	u = np.cross(p2-p1,p3-p1)
	return LA.norm(u) * 0.5

def getMeshTriArea( vtx, tri):
	nTri = tri.shape[0]
	areas = np.zeros(nTri)
	for t in range(nTri):
		v0 = vtx[tri[t,0]]
		v1 = vtx[tri[t,1]]
		v2 = vtx[tri[t,2]]
		areas[t] = Area3D( v0, v1, v2)
	return areas
#--------------------------------------------------------------
#rendering

#@njit(fastmath=True)
def createZeroPixels(_x0, _y0, _x1, _y1):
	zero_pixels_np = np.zeros( ( _x1-_x0+1, _y1-_y0+1, g_nPixelFormat)).astype(np.int32) # 4 = [x, y, z, nz]
	for x in range (0, _x1-_x0+1):
		for y in range(0, _y1-_y0+1):
			zero_pixels_np[x,y,0] = _x0+x;      zero_pixels_np[x,y,1] = _y0+y
	return zero_pixels_np

def numpyToOpen3D( np_pixels, _color0): # np_pixels has 4 floats of [x,y,z, nz]
	# Using trimesh instead of open3d
	temp_pixels = np.copy( np_pixels)
	vertices = temp_pixels[:,0:3]
	# Create a simple mesh representation with just points
	# For visualization purposes, we store vertices and color information
	return {'vertices': vertices, 'color': _color0}

def pxlsToTomo( pxls):
	global g_AABB2D
	(xmin, ymin, xmax, ymax) = g_AABB2D
	tomograph = createZeroPixels(xmin, ymin, xmax, ymax)
	for pxl in pxls:
		(x,y,z,nX,nY,nZ) = pxl
		tomograph[x][y] = z
	return tomograph

def create2DTomo( AABB2D, pxls):
	(_x0, _y0, _x1, _y1) = AABB2D
	pxl_2d = createZeroPixels( _x0, _y0, _x1, _y1)
	_mapToAdd = np.unique( np.copy(pxls), axis=0)
	for pixel in _mapToAdd:
		(a_x, a_y, a_z,nX,nY,nZ) = pixel
		pxl_2d[  int(a_x - _x0 + g_fMARGIN), int(a_y - _y0 +g_fMARGIN), 2] += a_z
	tomograph = [val[:,2] for val in pxl_2d]
	return tomograph

def updateAABB3D( AABB3D, pxls):
	if(pxls.size ==0):
		return AABB3D
	AABB3D[0] = min( AABB3D[0], np.min(pxls[:,0]))#x_min
	AABB3D[1] = min( AABB3D[1], np.min(pxls[:,1]))#y_min
	AABB3D[2] = min( AABB3D[2], np.min(pxls[:,2]))#z_min
	AABB3D[3] = max( AABB3D[3], np.max(pxls[:,0]))#x_max
	AABB3D[4] = max( AABB3D[4], np.max(pxls[:,1]))#y_max
	AABB3D[5] = max( AABB3D[5], np.max(pxls[:,2]))#z_max
	return AABB3D

def updateAABB2D( AABB2D, pxls):
	if(pxls.size ==0):
		return AABB2D
	AABB2D[0] = min( AABB2D[0], np.min(pxls[:,0]))#x_min
	AABB2D[1] = min( AABB2D[1], np.min(pxls[:,1]))#y_min
	AABB2D[2] = max( AABB2D[2], np.max(pxls[:,0]))#x_max
	AABB2D[3] = max( AABB2D[3], np.max(pxls[:,1]))#y_max
	return AABB2D

import matplotlib as mp
def Plot2DTomo(self):
	for id, (p_title, pxls, p_color) in enumerate( zip ( ('Vα', 'Vβ',  'Vo', 'Vtc', 'Vnv', 'Vss' ),
				(self.al_pxls, self.be_pxls,  self.Vo_pxls, self.TC_pxls, self.NVB_pxls, self.Vss_pxls),
				('Purples', 'Blues',  'Greys', 'Greens', 'Oranges', 'Reds' )   )):
		tomo = create2DTomo( self.AABB2D, pxls)
		# (z_min,z_max) = (-np.min(pxls[:,2]), np.max(pxls[:,2]))
		(z_min,z_max) = (0, np.max(pxls[:,2]))
		normalize = mp.colors.Normalize(vmin= z_min, vmax=z_max)
		plt.subplot(2,3,id+1);plt.title(p_title);  plt.imshow( tomo, aspect='equal', norm=normalize, cmap=plt.get_cmap(p_color))
	plt.show()


import plotly.graph_objects as go #4D graph
# import plotly.express as px #4D graph

def Plot3DPixels( self, title=""):#3D plots of pixel groups using Plotly
	AABB3D = np.array([1000,1000,1000,-1000,-1000,-1000])
	Plot3DPixels_data = []
	for p_title, p_name,  p_color, p_visible in zip (  g_PixelTitles, g_PixelVarNames, g_PixelColors, g_PixelVisible ):
		pxls = getattr(self, p_name)
		if pxls.shape[0] > 1e5:
			pxls = pxls[0::2]
		AABB3D = updateAABB3D( AABB3D, pxls)
		Plot3DPixels_data.append(
				go.Scatter3d(
					x=pxls[:,0],  y=pxls[:,1], z=pxls[:,2], name=p_title, mode='markers',
					customdata = [pxls[:,3],pxls[:,4],pxls[:,5]],
						marker=dict( size=1, color=p_color,  colorscale='Jet',line=dict(width=0.0),opacity=0.5),
    		visible = p_visible))
	import plotly.io as pio
	pio.renderers.default = "browser"
	fig = go.Figure( data=Plot3DPixels_data)
	(x0,y0,z0,x1,y1,z1) = AABB3D
	if y0!= y1 and x0 != x1:
		fig.update_scenes(aspectratio = dict( x=1.,y=(y1-y0) / (x1-x0), z=(z1-z0) / (x1-x0)))
	fig.update_scenes(camera_projection_type='orthographic')
	fig.update_layout( title=title)
	fig.show()

def Plot3DPixels_matplotlib(self):#screenshot of 3D plots using matplotlib, in case Plotly does not work,
	fig = plt.figure(figsize=(5, 5))
	ax = fig.add_subplot(111, projection='3d')
	for pxls,  p_color in zip (  g_PixelVarNames, g_PixelColors   ):
		pxls = getattr(self, pxls)
		self.scatter  = ax.scatter( pxls[:,0], pxls[:,1], pxls[:,2], alpha=0.5, color=p_color)
	plt.title("α pixel(purple),β pixel(blue),\n TC pixel(green), NV_b pixel(orange), NV_a pixel(yellow),\n Vo(gray), Vss(red)")
	plt.show()

import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection #showOptimals[]
from mpl_toolkits.axes_grid1 import make_axes_locatable#sphere graph
from scipy.interpolate import Rbf #sphere graph

def graphYP_3D( yaw_range, pitch_range, values, optimals, worsts, ax=None):
	ax = plt.gca() if (ax is None) else ax
	#interpolation for smooth surface.
	if yaw_range.shape[0] <= 37:
		(tht0, phi0) = np.meshgrid( toDegree(yaw_range), toDegree(pitch_range));
		rbf = Rbf( tht0, phi0, values, function='thin_plate',smooth=5, episilon=5)  #very slow.
		global g_PlotResolution
		interpol_t   = np.linspace(  yaw_range[0],   yaw_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
		interpol_p   = np.linspace(pitch_range[0], pitch_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
		(X, Y) = np.meshgrid( toDegree(interpol_t), toDegree(interpol_p));  Z = rbf( X, Y)
	else:#too many points.
		(X, Y) = np.meshgrid( toDegree(yaw_range), toDegree(pitch_range));   Z = values.reshape(yaw_range.shape[0],pitch_range.shape[0])
	#draw graph
	Z_min = np.min(Z);Z_max = np.max(Z)
	norm = colors.Normalize(vmin = Z_min,vmax = Z_max, clip = False)# add color w.r.t. R values
	ax.set_xlim3d( X[0,0], X[-1,-1])
	ax.set_ylim3d( Y[0,0], Y[-1,-1])
	ax.set_zlim3d( Z_min, Z_max)
	pc   = ax.plot_surface(  X, Y, Z,  facecolors = plt.cm.coolwarm(norm(Z)),  cmap=plt.cm.coolwarm,  alpha=0.4)
	#draw scale bar. https://matplotlib.org/3.1.1/gallery/axes_grid1/demo_colorbar_with_axes_divider.html
	m = cm.ScalarMappable(cmap=cm.coolwarm);   m.set_array(Z);
	divider = make_axes_locatable(ax);  cbar = plt.colorbar(m, ax=ax,fraction=0.03, pad=0.04)
	cbar.ax.set_title("Mss \n [mm]", size=10)
	#show optimal orientations. The blue sphere is the best optimal.
	if optimals.size > 0 and yaw_range.shape[0] <= 37:
		optX = toDegree(optimals[:,0]); optY = toDegree(optimals[:,1])
		optZ = rbf( optX, optY)
		optNorm=colors.Normalize(vmin = np.min(optZ), vmax = np.max(optZ), clip = False)
		ax.scatter(optX, optY, optZ, color='red', s=(2.-optNorm(optZ))*100.)
	if worsts.size > 0 and yaw_range.shape[0] <= 37:
		optX = toDegree(worsts[:,0]); optY = toDegree(worsts[:,1])
		optZ = rbf( optX, optY)
		optNorm=colors.Normalize(vmin = np.min(optZ), vmax = np.max(optZ), clip = False)
		ax.scatter(optX, optY, optZ, color='blue', s=(2.-optNorm(optZ))*100.)
	ax.set_xlabel('yaw [°]', fontsize=10)
	ax.set_ylabel('pitch [°]', fontsize=10)

def graphYP_2D( yaw_range, pitch_range, values, optimals, worsts, ax=None):
	ax = plt.gca() if (ax is None) else ax
	#interpolation for smooth surface.
	if yaw_range.shape[0] <= 37:
		(tht0, phi0) = np.meshgrid( toDegree(yaw_range), toDegree(pitch_range));
		rbf = Rbf( tht0, phi0, values)  #very slow.
		global g_PlotResolution
		interpol_t   = np.linspace(  yaw_range[0],   yaw_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
		interpol_p   = np.linspace(pitch_range[0], pitch_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
		(X, Y) = np.meshgrid( toDegree(interpol_t), toDegree(interpol_p));  Z = rbf( X, Y)
	else:#too many points.
		(X, Y) = np.meshgrid( toDegree(yaw_range), toDegree(pitch_range));   Z = values.reshape(yaw_range.shape[0],pitch_range.shape[0])
	#draw graph
	Z_min = np.min(Z);Z_max = np.max(Z)
	norm = colors.Normalize(vmin = Z_min,vmax = Z_max, clip = False)# add color w.r.t. R values
	pc = ax.contourf(  X, Y, Z,  cmap=plt.cm.coolwarm, norm = norm, levels=20, alpha=1.)
	#draw scale bar. https://matplotlib.org/3.1.1/gallery/axes_grid1/demo_colorbar_with_axes_divider.html
	m = cm.ScalarMappable(cmap=cm.coolwarm);   m.set_array(Z);
	divider = make_axes_locatable(ax);  cbar = plt.colorbar(m, ax=ax,fraction=0.03, pad=0.04)
	cbar.ax.set_title("Mtotal \n [g]", size=12)
	ax.set_aspect('equal', 'box')
	#show optimal orientations. The blue sphere is the best optimal.
	if optimals.size > 0:
		nOpt = optimals.shape[0]
		optX = toDegree(optimals[:,0]); optY = toDegree(optimals[:,1])
		if yaw_range.shape[0] <= 37:
			optZ = rbf( optX, optY)
			optNorm=colors.Normalize(vmin = np.min(optZ), vmax = np.max(optZ), clip = False)
			# ax.scatter(optX, optY, optZ, color=cm.coolwarm(optNorm(optZ)))#, s=(2.-optNorm(optZ))*100.)
		for i in range(nOpt):
			ax.annotate( 'o'+str(i+1), (optX[i], optY[i]),color='red')
		wstX = toDegree(worsts[:,0]); wstY = toDegree(worsts[:,1])
		for i in range(nOpt):
			ax.annotate( 'w'+str(i+1), (wstX[i], wstY[i]),color='blue')
		ax.set_xlabel('yaw [°]', fontsize=12)
		ax.set_ylabel('pitch [°]', fontsize=12)
	return ax

def graphYP_Spherical( yaw_range, pitch_range, R0, optimals=[], ax=None):#interpolate the given spherical coordinate data for better rendering.
	ax = plt.gca() if (ax is None) else ax

	#interpolation for smooth surface.
	(tht0, phi0) = np.meshgrid( yaw_range, pitch_range);  rbf = Rbf( tht0, phi0, R0)
	global g_PlotResolution
	interpol_t   = np.linspace(  yaw_range[0],   yaw_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
	interpol_p   = np.linspace(pitch_range[0], pitch_range[-1], num=g_PlotResolution, endpoint=True, dtype=np.float32)
	(tht1, phi1) = np.meshgrid( interpol_t, interpol_p);  R1 = rbf( tht1, phi1)
	(X, Y, Z) = toCartesian( tht1/1., phi1, R1)#Note: tht1/2. is  to set theta's range as [0~2pi]

	#draw graph
	R_min = np.min(R1);R_max = np.max(R1)
	norm = colors.Normalize(vmin = R_min,vmax = R_max, clip = False)# add color w.r.t. R values
	ax.set_xlim3d(-R_max,R_max)
	ax.set_ylim3d(-R_max,R_max)
	ax.set_zlim3d(-R_max,R_max)
	pc   = ax.plot_surface(  X, Y, Z,  \
			facecolors = plt.cm.coolwarm(norm(R1)),  cmap=plt.cm.coolwarm,  alpha=0.8)

	#draw scale bar. https://matplotlib.org/3.1.1/gallery/axes_grid1/demo_colorbar_with_axes_divider.html
	m = cm.ScalarMappable(cmap=cm.coolwarm);   m.set_array(R1);
	divider = make_axes_locatable(ax);  cb = plt.colorbar(m, ax=ax)

	#show optimal orientations. The biggest red circle is the best optimal.
	if(optimals != []):
		optR = rbf(optimals[:,0], optimals[:,1])
		optNorm=colors.Normalize(vmin = np.min(optR), vmax = np.max(optR), clip = False)
		(optX, optY, optZ) = toCartesian( optimals[:,0]/2., optimals[:,1], optR) #Note: tht1/2. is due to theta's range [0~2pi]
		ax.scatter(optX, optY, optZ, color=cm.coolwarm(optNorm(optR)), s=(2.-optNorm(optR))*100.)

	return ax

def graphYPR( X, Y, Z, D, optimals, ax=None):
	ax = plt.gca() if (ax is None) else ax
	img = ax.scatter(  X, Y, Z, c=D, cmap=plt.cm.coolwarm)
	divider = make_axes_locatable(ax)
	plt.colorbar(img, ax=ax)
	return ax

def graphYPR_Plotly( X, Y, Z, D, optimals):
	fig = go.Figure(data=go.Volume(
			x=toDegree(X).flatten(), y=toDegree(Y).flatten(), z=toDegree(Z).flatten(),value= D.flatten(),
			surface_count=17,
			isomin=np.min( D.flatten()), isomax=np.max( D.flatten()),
			opacity=0.5, # max opacity
			opacityscale=[[0, 1], [0.3, 0.2], [0.8, 0.2], [1, 1]],
			colorscale='bluered' ))
	#show optimal orientations. The biggest blue sphere is the 1st optimal.
	fig.add_trace(go.Scatter3d(
				mode='markers',x=toDegree(optimals[:,0]), y=toDegree(optimals[:,1]),z=toDegree(optimals[:,2]),
				marker=dict(color=['rgb(0, 0, 255)', 'rgb(50, 0, 200)',
							 'rgb(100, 0, 150)', 'rgb(150,0,100)', 'rgb(200, 0,0 )'],size=[30,25,20,15,10], showscale=False  ) ))
	fig.show()


def PrintSlotInfo(self, X=-1,Y=-1): #print pxls in (X,Y) slot. for debugging
	if( X>-1 and Y>-1):
		for p_name, pxls in zip ( g_PixelEnums, g_PixelVarNames):
			pxls = getattr(self, pxls)
			print( p_name, "=\n", pxls[np.where( (pxls[:,0] == X) & (pxls[:,1] == Y)) ] ,"\n")

def Print(self):
	print("-------Volume info.----")
	print('Va=', self.Va, ', Vb=',  self.Vb, ', Vtc=',   self.Vtc,  ', Vnv=',   self.Vnv)
	print('Vo=', self.Vo, ', Vss=', self.Vss,', Vclad=', self.Vclad,', Vcore=', self.Vcore)
	print("-------Mass info.------")
	print("Mcore=", self.Mcore,", Mclad=", self.Mclad)
	print("Mo=", self.Mo, ", Mss=", self.Mss, ", Mtotal=", self.Mtotal)

#--------------------------------------------------------------
#finding optimals

def smallestN_indices(data1D, N, maintain_order=False):#find N optimal values in list 'a', neglecting duplicate values
	data1D = np.round(data1D * 10. ) * 0.1
	best_IDs = data1D.argsort()
	worst_IDs = data1D.argsort()[::-1]
	if best_IDs.size >=N:
		return (best_IDs[:N],worst_IDs[:N])
	return (best_IDs, worst_IDs)

def paramsYP( yaw_range, pitch_range, theta_c):
	params = np.empty( [0,5], dtype=np.float32)
	sizeY = yaw_range.size ; sizeP = pitch_range.size ; sizeYP = sizeY * sizeP
	thread_id = 0#RAY deug
	roll = 0 #roll directional rotation is not needed.
	for pitch in pitch_range:
		for yaw in yaw_range:
			params = np.append( params, np.array([[yaw,pitch,roll,theta_c, thread_id+ g_fMARGIN]]), axis=0)
			thread_id = thread_id + 1
	return ( params, sizeY, sizeP, sizeYP)

def findOptimals(YPR, data, nOptimal):#data is 1D array
	(best_IDs, worst_IDs) = smallestN_indices( data, nOptimal, maintain_order=True)
	nOptimal = min(best_IDs.size, nOptimal)
	optimal_YPRs = np.zeros((nOptimal,4)) #[yaw, pitch, roll=0, Mtotal]
	worst_YPRs   = np.zeros((nOptimal,4)) #[yaw, pitch, roll=0, Mtotal]
	for i in range(nOptimal):
		opt_ID = best_IDs[i]; wst_ID = worst_IDs[i]
		optMtotal = data[opt_ID];wstMtotal = data[wst_ID]

		(yaw,pitch, roll) = (YPR[opt_ID,0], YPR[opt_ID,1], YPR[opt_ID,2])
		optimal_YPRs[i]    =  np.array([yaw, pitch, roll, optMtotal] )
		print( i+1,"st optimal is at [", FStr( toDegree([yaw,pitch,roll])),
						"], Mss=", FStr( optMtotal, precision=3))

		(yaw,pitch, roll) = (YPR[wst_ID,0], YPR[wst_ID,1], YPR[wst_ID,2])
		worst_YPRs[i]    =  np.array([yaw, pitch, roll, wstMtotal] )
		print( i+1,"st worst is at [", FStr( toDegree([yaw,pitch,roll])),
						"], Mss=", FStr( wstMtotal, precision=3))
	return (optimal_YPRs, worst_YPRs)

# import quaternion
# def rotateVecByQt( yaw, pitch, vec0):
#   qn = quaternion.from_spherical_coords(yaw, pitch)
#   _zeros = np.zeros(vec0.shape[0])
#   qvec0 = np.insert( vec0, 0, _zeros, axis=1)
#   qvecsq = quaternion.as_quat_array(qvec0)
#   qvec1 = qn * qvecsq * qn.conjugate()
#   vec1 = quaternion.as_float_array(qvec1)[:,1:]
#   return vec1

from scipy.spatial.transform import Rotation #quaternion
import copy
def drawOptimals( mesh0, optimals, optID, title, ax=None): # show meshes in optimal orientation and their Mtotal values. opts = lists of [y,p,r]
	ax = plt.gca() if (ax is None) else ax
	mesh1 = mesh0#copy.deepcopy( mesh0)
	(yaw, pitch, roll ) = optimals[optID,0:3]
	tri   = np.asarray( mesh1.faces)
	vtx   = np.asarray( copy.deepcopy(mesh1.vertices))
	qn    = Rotation.from_euler('xyz', [[yaw, pitch, roll]], degrees=False)
	vtx   = qn.apply(vtx)
	# vtx = rotateVecByQt( yaw, pitch, vtx)
	mesh = Poly3DCollection(vtx[tri],linewidths=0.1)
	mesh.set_edgecolor('k')
	(vtx_min, vtx_max, _) = getBoundary( vtx)
	ax.set_xlim( vtx_min[0], vtx_max[0])
	ax.set_ylim( vtx_min[1], vtx_max[1])
	ax.set_zlim( vtx_min[2], vtx_max[2])
	ax.set_box_aspect((np.ptp(vtx[:,0]), np.ptp(vtx[:,1]), np.ptp(vtx[:,2])))
	ax.add_collection3d(mesh)
	title = str(optID+1) + str('th ') + title + str(' at \n') + str(FStr(toDegree(optimals[optID, 0:3]))) +'\n Mtotal=' + str(FStr(optimals[optID,3],precision = 3)) + str('[g]')
	ax.set_title( title, fontsize=10)
	return ax

def Plot3D(mesh0, yaw_range, pitch_range, value_data, optimals=[], worsts=[]):
	nVtx = np.asarray( mesh0.vertices).shape[0]
	if( nVtx > 100_000):
		# Using trimesh for simplification instead of open3d
		bounds = mesh0.bounds
		voxel_size = max(bounds[1] - bounds[0]) / 8
		mesh0 = mesh0.simplify_consecutive_duplicate()
		mesh0 = mesh0.simplify_quadratic_decimation(target_reduction=0.5)
	nOpts = optimals.shape[0] if(optimals.size > 0 ) else 0
	fig = plt.figure(figsize=(4*nOpts,8))
	gs1 = fig.add_gridspec(2, nOpts+1, width_ratios=[2,*([1]*nOpts)])
	ax00 = fig.add_subplot(gs1[0,0])
	ax10 = fig.add_subplot(gs1[1,0], projection='3d')
	ax_opts = [fig.add_subplot(gs1[0,optID+1], projection='3d') for optID in range(nOpts)]
	ax_wsts = [fig.add_subplot(gs1[1,wstID+1], projection='3d') for wstID in range(nOpts)]

	graphYP_2D( yaw_range, pitch_range, value_data, optimals, worsts, ax00)
	graphYP_3D( yaw_range, pitch_range, value_data, optimals, worsts, ax10)

	if optimals.size > 0:
		[ drawOptimals( mesh0, optimals,optID, 'optimal', ax = ax_opts[optID], ) for optID in range(nOpts) ]
	if worsts.size > 0:
		[ drawOptimals( mesh0, worsts, wstID, 'worst' , ax = ax_wsts[wstID], ) for wstID in range(nOpts) ]

	if optimals.size > 0:
		plt.tight_layout()
		import os
		global g_input_mesh_filename
		path0 = os.path.dirname(os.path.abspath(g_input_mesh_filename))
		fig_name = os.path.basename(g_input_mesh_filename).replace( ".", "_")
		# fig.savefig( path0 + "\\" + fig_name + "_step" + str(int(toDegree(yaw_range[1]+g_fMARGIN))) + ".png", dpi=200)
	save_path = os.environ.get("TOMO_PLOT3D_SAVE", "").strip()
	if save_path:
		save_dir = os.path.dirname(os.path.abspath(save_path))
		if save_dir:
			os.makedirs(save_dir, exist_ok=True)
		fig.savefig(save_path, dpi=int(os.environ.get("TOMO_PLOT3D_DPI", "100")))
		print("wrote", save_path)
	if os.environ.get("TOMO_NO_SHOW", "0").lower() not in ("1", "true", "yes", "on"):
		plt.show()
	else:
		plt.close(fig)

#--------------------------------------------------------------
#mesh I/O
import trimesh

def LoadInputMesh(filename):
	import os.path
	import sys
	if( not os.path.isfile(filename) ):
		print('[ERROR] File Does not Exists: ' + filename)
		sys.exit(0)
	if( not os.path.isfile(g_CppDLLFileName) ):
		print('[ERROR] C++ Dll Does not Exists: ' + g_CppDLLFileName)
		sys.exit(0)
	# Using trimesh instead of open3d
	mesh0 = trimesh.load(filename, force='mesh')
	(g_mesh0_min, g_mesh0_max, g_mesh0_center) = getBoundary( mesh0.vertices)
	mesh0.vertices = mesh0.vertices - g_mesh0_center
	global g_mesh0_surface_area
	g_mesh0_surface_area = mesh0.area
	vtx   = np.asarray( mesh0.vertices).astype(np.float32) # 'TOMO_FLOAT32' type of C++ Dll.
	tri   = np.asarray( mesh0.faces).astype(np.int32)  # 'MESH_ELE_ID_TYPE' type of C++ Dll.
	tri_nrm   = np.asarray( mesh0.face_normals).astype(np.float32) # 'TOMO_FLOAT32' type of C++ Dll.
	vtx_nrm   = np.asarray( mesh0.vertex_normals).astype(np.float32)
	tri_area  = getMeshTriArea( vtx, tri)
	# Compute convex hull using trimesh
	chull = mesh0.convex_hull
	chull_tri   = np.asarray( chull.faces).astype(np.int32)  # 'MESH_ELE_ID_TYPE' type of C++ Dll.
	chull_vtx = np.array(chull.vertices).astype(np.float32)
	chull_trinrm   = np.asarray( chull.face_normals).astype(np.float32) # 'TOMO_FLOAT32' type of C++ Dll.
	tr_center   = np.average( vtx[tri], axis=1).astype(np.float32)
	global g_input_mesh_filename
	g_input_mesh_filename = filename
	return (mesh0, tri, vtx, vtx_nrm, tri_nrm, tri_area, tr_center, chull_tri, chull_vtx, chull_trinrm)

#end of io-functions.

import math
def getRotationMatrix( ga, be, al):
	mat4x4 = np.eye(4)
	cos_al = math.cos(al)
	cos_be = math.cos(be)
	cos_ga = math.cos(ga)

	sin_al = math.sin(al)
	sin_be = math.sin(be)
	sin_ga = math.sin(ga)

	mat4x4[0,0] = cos_al * cos_be
	mat4x4[0,1] = cos_al * sin_be * sin_ga - sin_al*  cos_ga
	mat4x4[0,2] = cos_al * sin_be * cos_ga + sin_al * sin_ga

	mat4x4[1][0] = sin_al * cos_be
	mat4x4[1][1] = sin_al * sin_be * sin_ga + cos_al * cos_ga
	mat4x4[1][2] = sin_al * sin_be * cos_ga - cos_al * sin_ga

	mat4x4[2][0] = - sin_be
	mat4x4[2][1] = cos_be * sin_ga
	mat4x4[2][2] = cos_be * cos_ga

	return mat4x4
