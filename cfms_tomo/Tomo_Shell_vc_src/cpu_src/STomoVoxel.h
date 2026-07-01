#pragma once
#include <vector>//stl
#include <functional>
#include "../Tomo_types.h"
#include "STomoPixel.h"

using namespace Tomo;

class DLLEXPORT STomoVoxel //integer-based data
{ 
public:
  STomoVoxel(FLOAT32* _pxl3d=nullptr, FLOAT32 *_nrm3d=nullptr);
  STomoVoxel(const STomoPixel&);
  STomoVoxel(const STomoVoxel& Source);
    void	operator=(const STomoVoxel& Source);
    void	_Copy(const STomoVoxel& Source);
    void	DumpTo(FLOAT32* _data_2f) const;
  ~STomoVoxel();

  void	Reset(void);
  void	Init(void);

  static const int nfData = 6;
  static const int sfData = sizeof(FLOAT32) * nfData;
  union
  { struct {   FLOAT32	x, y, z, nx, ny, nz;   };
    struct {   FLOAT32	crd[3],nrm[3];};
    FLOAT32 fData[nfData];
  };

  int    iTypeByte;//at least 10 bits.
};


DLLEXTERN template class DLLEXPORT std::vector<STomoVoxel>;
DLLEXPORT typedef std::vector<STomoVoxel>		 TVVector;
DLLEXPORT typedef TVVector::reverse_iterator				 TVReverseIterator;
DLLEXPORT typedef TVVector::iterator				 TVIterator;
DLLEXPORT typedef TVVector::const_iterator	 TVConstIterator;
DLLEXPORT typedef TVVector**  TVVectorpp;

DLLEXPORT TVVector& operator<<(TVVector& lhs, const TVVector& rhs);
DLLEXPORT bool operator==(const STomoVoxel&lhs, const STomoVoxel& rhs);
DLLEXPORT TVIterator _find(TVVector& pxls, const STomoVoxel& pixel);

DLLEXPORT STomoVoxel getMid(const STomoVoxel& a, const STomoVoxel& b);
DLLEXPORT FLOAT32 distance( const STomoVoxel& a, const STomoVoxel& b);

DLLEXPORT void  moveVoxelCentersToOrigin(TVVector& v);
DLLEXPORT void  moveVoxelCornersToOrigin(TVVector& v);
DLLEXPORT void  rotateVoxels(TVVector& v, FLOAT32 yaw, FLOAT32 pitch, FLOAT32 roll);
//DLLEXPORT void  getCVVoxels(TVVector& CV_vxls, S3DPrinterInfo* info, TOMO_FLOAT32 yaw, TOMO_FLOAT32 pitch, TOMO_FLOAT32 roll);
