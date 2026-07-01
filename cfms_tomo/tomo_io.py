#---------------------------------------------------------
# interface to Cpp Dll (ctypes)

import numpy as np
import ctypes as ct

Cptr1i  = ct.POINTER(ct.c_short)#16bit
Cptr1iL  = ct.POINTER(ct.c_long)#32bit. for element IDs'
Cptr1d  = ct.POINTER(ct.c_float)#32bit

def np_to_Cptr1i( X): 	return X.ctypes.data_as(Cptr1i)
def np_to_Cptr1iL( X):	return X.ctypes.data_as(Cptr1iL)
def np_to_Cptr1d( X):	return X.ctypes.data_as(Cptr1d)

def Cptr1i_to_np(ptr, rows):
	if rows == 0:	return []
	return np.array(ptr[:rows]).astype(np.int16)

def Cptr1iL_to_np(ptr, rows):
	if rows == 0:return []
	return np.array(ptr[:rows]).astype(np.int32)

def Cptr1d_to_np(ptr, rows):
	if rows == 0:return []
	return np.array(ptr[:rows]).astype(np.float32)


#--------------------------------------------------------------
#strings
def my_FStr(float_value, precision=1):
	return "{0:.{precision}f}".format(float_value, precision=precision)
def my_toRadian(degree):	return degree * np.pi / 180.
def my_toDegree(radian):	return radian * 180. / np.pi

FStr     = np.vectorize( my_FStr)
toRadian = np.vectorize( my_toRadian)
toDegree = np.vectorize( my_toDegree)
#--------------------------------------------------------------
import time
import datetime
def StartTimer(str=""):
  if len(str)>0:
    print(str)
  return time.time()

def EndTimer( start_time, filename):
	end_time = time.time();    total_time = end_time - start_time
	print(filename + '= ', datetime.timedelta(seconds=total_time), ' seconds \n' )

def smallestN_indices(data1D, N, maintain_order=False):#find N optimal values in list 'a', neglecting duplicate values
	data1D = np.round(data1D * 10. ) * 0.1
	best_IDs = data1D.argsort()
	worst_IDs = data1D.argsort()[::-1]
	if best_IDs.size >=N:
		return (best_IDs[:N],worst_IDs[:N])
	return (best_IDs, worst_IDs)


def findOptimals(YPR, Mss,  bVerbose = False, nOptimalToFind = 1):#data is 1D array
	from cfms_tomo.tomo_result import TomoResult
	(best_IDs, worst_IDs) = smallestN_indices( Mss, nOptimalToFind, maintain_order=True)
	nOptimalToFind = min(best_IDs.size, nOptimalToFind)
	bests 	= []
	worsts  = []
	for i in range(nOptimalToFind):
		b_id = best_IDs[i]
		B    =  TomoResult( [YPR[b_id,0], YPR[b_id,1], YPR[b_id,2],
                        	0, Mss[b_id], Mss[b_id]])

		w_ID = worst_IDs[i]
		W    =  TomoResult( [YPR[w_ID,0], YPR[w_ID,1], YPR[w_ID,2],
                        0, Mss[w_ID], Mss[w_ID]] )

		if bVerbose:
			B.print()
			W.print()

		bests.append( B)
		worsts.append(W)
	return (bests[0], worsts[0])

