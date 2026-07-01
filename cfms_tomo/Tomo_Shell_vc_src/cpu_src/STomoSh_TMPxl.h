#pragma once
#include "STPSlot.h"
#include "STomoVoxelSpaceInfo.h"
#include "STomoSh_Base.h"

using namespace Tomo;

class DLLEXPORT STomoSh_TMPxl : public STomoSh_Base
{
public:
  STomoSh_TMPxl();
  //STomoNV(S3DPrinterInfo _info);
  STomoSh_TMPxl(const STomoSh_TMPxl& Source);
    void	operator=(const STomoSh_TMPxl& Source);
    void	_Copy(const STomoSh_TMPxl& Source);
  ~STomoSh_TMPxl();

  void	Reset(void);
  void	Init(void);
  
  //void  Rotate(void);//(yaw, pitch, roll) 회전 후 origin으로 평행이동.
  void  Pixelize();//픽셀화 후 slot에 바로 넣기.
    void triPixel(
    FLOAT32* v0, FLOAT32* v1, FLOAT32* v2,
    FLOAT32* n0, FLOAT32* n1, FLOAT32* n2,
    TPVector& tri_pxls);
    TPVector  slotsToPxls(enumPixelType _type);//for rendering. time consuming. 
    void      pxlsToSlots(TPVector& tri_pxls);
      void inline _insert_to_pxls(const STomoPixel& pxl);
  void  Pairing(void);//slot paring.
  void  Calculate(void);//get Vss value
  void  GenerateBed(void);

  TPVector GetSSPixels(bool _bUseExplicitSS);

};
