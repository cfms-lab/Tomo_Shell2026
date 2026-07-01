#pragma once
#include <vector>//stl
#include <functional>
#include "../Tomo_types.h"
#include "STomoVoxel.h"
#include "STomoAABB3Df.h"

using namespace Tomo;

class DLLEXPORT STomoTriangle //integer-based data
{ 
public:
  STomoTriangle();
  STomoTriangle(const STomoVoxel &, const STomoVoxel&, const STomoVoxel&);
  STomoTriangle(const STomoTriangle& Source);
    void	operator=(const STomoTriangle& Source);
    void	_Copy(const STomoTriangle& Source);
    void	DumpTo(FLOAT32* _vtx3f_nrm1f) const;
  ~STomoTriangle();

  void	Reset(void);
  void	Init(void);

  static const int iShape = 3;
  STomoVoxel Vtx[iShape];

  STomoAABB3Df AABB;

  std::vector<STomoTriangle> DivideTo4(void) const;
  FLOAT32 GetCurcumDiameter(void) const;

  void  Print(void);//debug
  
};


DLLEXTERN template class DLLEXPORT std::vector<STomoTriangle>;
DLLEXPORT typedef std::vector<STomoTriangle>		 TTriVector;
DLLEXPORT typedef TTriVector::reverse_iterator				 TTriReverseIterator;
DLLEXPORT typedef TTriVector::iterator				 TTriIterator;
DLLEXPORT typedef TTriVector::const_iterator	 TTriConstIterator;
DLLEXPORT typedef TTriVector**  TTriVectorpp;

DLLEXPORT void triDivide4(TTriVector& tri_vec, const STomoTriangle& tri, FLOAT32 size);

 

