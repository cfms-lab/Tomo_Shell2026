#pragma once
#pragma warning ( disable:4251)
#pragma warning ( disable:4819) //warning C4819 : ���� �ڵ� ������(949)���� ǥ���� �� ���� ���ڰ� ���Ͽ� ��� �ֽ��ϴ�.�����Ͱ� �սǵ��� �ʰ� �Ϸ��� �ش� ������ �����ڵ� �������� �����Ͻʽÿ�.

#ifdef _CREATING_DLL_
#define DLLEXPORT __declspec(dllexport)
#define DLLEXTERN
#else
 #ifdef _USING_DLL_
  #define DLLEXPORT __declspec(dllimport)
  #define DLLEXTERN extern 
  //https://rookiecj.tistory.com/112
  #else
  #define DLLEXPORT 
  #define DLLEXTERN 
  #endif
#endif

//#define _EZAIR_THETAC_ZERO //Vss = Vtc - Vo. obsolete.. for test.

#define _USE_VTX_NRM_FOR_PIXEL
#define _USE_BRIEF_SLOT_PAIRING //GPGPU-friendly,
#define _USE_CUDA_FOR_TOMONV

namespace Tomo
{
  typedef float       FLOAT32;//4byte. ctype. = np.float32 = ctypes.f_loat
  typedef short int   INT16;//2byte = np.int16 = ctypes.c_short
  typedef int         MESH_ELE_ID_TYPE;//4byte = np.int32 = ctypes.c_int. nVtx, nTri, rpTri0

  //CPU version TomoNV types
  typedef long int      VOXEL_ID_TYPE;//4 byte. https://docs.microsoft.com/ko-kr/cpp/cpp/data-type-ranges?view=msvc-170
  typedef short int     SLOT_BUFFER_TYPE;//cpu version. 2byte, [-32,767~32,767]
  typedef unsigned int  BIT_BUFFER_TYPE;//4byte. [0~4,294,967,295]


  const static int g_nPixelFormat = 6;
  const static FLOAT32 g_fNORMALFACTOR = FLOAT32(1000.);
  const static FLOAT32 g_fMARGIN = FLOAT32(0.001);


  //DLLEXPORT const int iVOXELFACTOR = 1;//1==256 voxel. 2== 512 voxel...

  enum class enumPixelType {
    //espAll  = -1,
    eptAl = 0,
    eptBe = 1,
    eptSSB = 2,
    eptSSA = 3,
    eptSS = 4,
    eptBed = 5,
    eptVo = 6,
    eptVss = 7,
    eptTC = 8,
    eptNVB = 9,
    eptNVA = 10,
    eptNumberOfSubPixels
  };

const static int g_nPixelType = static_cast<int>(enumPixelType::eptNumberOfSubPixels);


enum class enumBedType {
    ebtNone = 0,
    ebtBrim = 1,
    ebtRaft = 2,
    ebtSkirt = 3
  };
  

const SLOT_BUFFER_TYPE typeAl = 1 << (int)enumPixelType::eptAl;//1
const SLOT_BUFFER_TYPE typeBe = 1 << (int)enumPixelType::eptBe;//2
const SLOT_BUFFER_TYPE typeSSB = 1 << (int)enumPixelType::eptSSB;//4
const SLOT_BUFFER_TYPE typeSSA = 1 << (int)enumPixelType::eptSSA;//8
const SLOT_BUFFER_TYPE typeSS = 1 << (int)enumPixelType::eptSS;//16
const SLOT_BUFFER_TYPE typeBed = 1 << (int)enumPixelType::eptBed;//32
const SLOT_BUFFER_TYPE typeVo = 1 << (int)enumPixelType::eptVo;//64
const SLOT_BUFFER_TYPE typeVss = 1 << (int)enumPixelType::eptVss;//128
const SLOT_BUFFER_TYPE typeTC = 1 << (int)enumPixelType::eptTC;//256
const SLOT_BUFFER_TYPE typeNVB = 1 << (int)enumPixelType::eptNVB;//512
const SLOT_BUFFER_TYPE typeNVA = 1 << (int)enumPixelType::eptNVA;//1024


  DLLEXPORT FLOAT32 inline _dot(FLOAT32* a, FLOAT32* b);
  DLLEXPORT FLOAT32 inline _abs(FLOAT32 value);
  DLLEXPORT INT16   inline _abs(INT16 value);
  DLLEXPORT FLOAT32 inline _min(FLOAT32 a, FLOAT32 b);
  DLLEXPORT FLOAT32 inline _max(FLOAT32 a, FLOAT32 b);
  DLLEXPORT INT16   inline _min(INT16 a, INT16 b);
  DLLEXPORT INT16   inline _max(INT16 a, INT16 b);
  DLLEXPORT SLOT_BUFFER_TYPE   inline _round(FLOAT32 a);
  DLLEXPORT FLOAT32 inline _toDegree(FLOAT32 _radian);
  DLLEXPORT FLOAT32 inline _toRadian(FLOAT32 _degree);
  DLLEXPORT void inline giveMargin(FLOAT32* v);
  DLLEXPORT void inline _bary_product(
    /*inputs*/ FLOAT32* p0, FLOAT32* p1, FLOAT32* p2,
    FLOAT32  u, FLOAT32   v, FLOAT32   w,
    /*output*/ FLOAT32* pxl);
  DLLEXPORT bool  _getBaryCoord(
    /*inputs*/ FLOAT32* p, FLOAT32* a, FLOAT32* b, FLOAT32* c,
    /*output*/ FLOAT32& u, FLOAT32& v, FLOAT32& w);
  DLLEXPORT void  inline QuickSort(SLOT_BUFFER_TYPE A[], size_t I[], size_t lo, size_t hi);

  DLLEXPORT void  uintTo32Bools(BIT_BUFFER_TYPE _byte, bool _bBits[8]);
  DLLEXPORT SLOT_BUFFER_TYPE  inline toTypeByte(enumPixelType type);

  void  startTimer(void);
  void  endTimer(const char* title = nullptr);

  DLLEXPORT FLOAT32  getDist3D(FLOAT32* a, FLOAT32* b);
  DLLEXPORT FLOAT32   getTriArea3D(FLOAT32* a, FLOAT32* b, FLOAT32* c);

}

