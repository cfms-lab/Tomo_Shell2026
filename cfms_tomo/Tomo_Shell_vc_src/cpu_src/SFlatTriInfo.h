#pragma once
#include "../Tomo_types.h"


using namespace Tomo;
static const int nFlatTriInfoSize = 12;//== # of floats in struct FlatTri.

class DLLEXPORT SFlatTriInfo
{
public:
  SFlatTriInfo();
  SFlatTriInfo(const SFlatTriInfo& Source);
  void	operator=(const SFlatTriInfo& Source);
  void	_Copy(const SFlatTriInfo& Source);
  ~SFlatTriInfo();

  void	Reset(void);
  void	Init(void);

  static const int nfData = nFlatTriInfoSize;
  static const int sfData = sizeof(FLOAT32) * nfData;
  union
  {
    struct
    {
      FLOAT32 vtx0[3];//꼭지점의 상대좌표. (0,0)~(16,16) 및 노말벡터의 z 성분.
      FLOAT32 vtx1[3];
      FLOAT32 vtx2[3];
      FLOAT32 tri_nrm[3];
      //FLOAT32 stride[4];
    } FlatTriInfo;
    FLOAT32 fData[nfData];
  };

};

