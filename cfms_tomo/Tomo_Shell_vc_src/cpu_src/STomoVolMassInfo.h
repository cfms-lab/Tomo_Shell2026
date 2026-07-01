#pragma once
#include "..\Tomo_types.h"
#include "S3DPrinterInfo.h"

using namespace Tomo;

class DLLEXPORT STomoVolMassInfo
{
public:
  STomoVolMassInfo();
  STomoVolMassInfo(const STomoVolMassInfo& Source);
  void	operator=(const STomoVolMassInfo& Source);
  void	_Copy(const STomoVolMassInfo& Source);
  ~STomoVolMassInfo();

  void	Reset(void);
  void	Init(void);

  static const int ndData = 22;
  static const int sdData = sizeof(FLOAT32) * ndData;
  union
  {
     struct {
      FLOAT32	Va/*0*/, Vb, Vtc, Vnv, \
        Vss/*4*/, Vss_clad, Vss_core, Ass_clad/*surface area of  s.s.. = ssb - ssa*/, \
        Vo/*8*/, Vo_clad, Vo_core, \
        Vbed/*11*/, Mbed, \
        Mss/*13*/, Mss_clad, Mss_core,
        Mo/*16*/, Mo_clad, Mo_core, \
        Mtotal/*19*/,SS_vol/*for debug*/;
    };
    FLOAT32 dData[ndData];
  };

  void  VolToMass(const S3DPrinterInfo& printer_info);
};
