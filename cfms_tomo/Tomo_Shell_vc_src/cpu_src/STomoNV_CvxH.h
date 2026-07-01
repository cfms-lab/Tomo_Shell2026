#pragma once
#include "STPSlot.h"
#include "STomoVoxelSpaceInfo.h"
#include "STomoNV_Base.h"

using namespace Tomo;

class DLLEXPORT STomoNV_CvxH : public STomoNV_Base
{
public:
  STomoNV_CvxH();
  //STomoNV_CvxH(S3DPrinterInfo _info);
  STomoNV_CvxH(const STomoNV_CvxH& Source);
  void	operator=(const STomoNV_CvxH& Source);
  void	_Copy(const STomoNV_CvxH& Source);
  ~STomoNV_CvxH();

  void	Reset(void);
  void	Init(void);

  void  Rotate(void);
  void  Pixelize(const TVVector& CVV_vxls);
  void  GenerateBed(void) { }
  void  Pairing(void);//get TC pixel only, via GetVtc_Convex()
  void  Calculate(void);//do nothing.


  //convex test : 얘들은 마지막에 한번만 실행된다. (y,p) 방향별 Vtc값이 있어야 됨.
  FLOAT32  getCHVtc(void);
  FLOAT32  getCHVss(void);

  int  getCHBottom(FLOAT32* shadow_vec);
  FLOAT32 vtxToCHDist(FLOAT32* cnt_v3, FLOAT32* shadow_v3, FLOAT32* chull_v3);

  FLOAT32 shadow_v3[3];

};


