#include "pch.h"
#include "Tomo_types.h"
#include "cpu_src/STomoPixel.h"
#include <vector>
#include <algorithm>  // std::find_if

#include <chrono>
#include <iostream>//std::cout


namespace Tomo
{

  FLOAT32 inline _dot(FLOAT32* a, FLOAT32* b)
  {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  FLOAT32 inline _abs(FLOAT32 value)
  {
    return (value >= 0.) ? value : -value;
  }

  INT16 inline _abs(INT16 value)
  {
    return (value >= 0) ? value : -value;
  }

  FLOAT32 inline _min(FLOAT32 a, FLOAT32 b)
  {
    return (a <= b) ? a : b;
  }

  INT16 inline _min(INT16 a, INT16 b)
  {
    return (a <= b) ? a : b;
  }

  FLOAT32 inline _max(FLOAT32 a, FLOAT32 b)
  {
    return (a >= b) ? a : b;
  }

  INT16 inline _max(INT16 a, INT16 b)
  {
    return (a >= b) ? a : b;
  }

  SLOT_BUFFER_TYPE   inline _round(FLOAT32 a)
  {
    int a10 = int(a * 10);
    int digit1 = a10 - int(a)*10;
    if(digit1>=5) return int(a+1);
    else          return int(a);
  }

  FLOAT32 inline _toDegree(FLOAT32 _radian)
  {
    return FLOAT32(_radian * 180. / 3.141592);
  }

  FLOAT32 inline _toRadian(FLOAT32 _degree)
  {
    return FLOAT32(_degree / 180. * 3.141592);
  }


  void inline giveMargin(FLOAT32* v)
  {
    v[0] += g_fMARGIN;
    v[1] += g_fMARGIN;
    v[2] += g_fMARGIN;
  }

  void inline _bary_product(
    /*inputs*/ FLOAT32* p0, FLOAT32* p1, FLOAT32* p2,
    FLOAT32  u, FLOAT32   v, FLOAT32   w,
    /*output*/ FLOAT32* pxl)
  {
    for (int i = 0; i < 3; i++)
    {
      pxl[i] = p0[i] * u + p1[i] * v + p2[i] * w;
    }
  }

  bool  _getBaryCoord(
    /*inputs*/ FLOAT32* p, FLOAT32* a, FLOAT32* b, FLOAT32* c,
    /*output*/ FLOAT32& u, FLOAT32& v, FLOAT32& w)
  {
    FLOAT32 v0[3] = { b[0] - a[0], b[1] - a[1], 0. };
    FLOAT32 v1[3] = { c[0] - a[0], c[1] - a[1], 0. };
    FLOAT32 v2[3] = { p[0] - a[0], p[1] - a[1], 0. };

    FLOAT32 d00 = _dot(v0, v0);
    FLOAT32 d01 = _dot(v0, v1);
    FLOAT32 d11 = _dot(v1, v1);
    FLOAT32 d20 = _dot(v2, v0);
    FLOAT32 d21 = _dot(v2, v1);

    FLOAT32 denom = d00 * d11 - d01 * d01;

    if (_abs(denom) > g_fMARGIN)
    {
      v = (d11 * d20 - d01 * d21) / denom;
      w = (d00 * d21 - d01 * d20) / denom;
      u = 1.0 - v - w;
      if (u >= -g_fMARGIN && v >= -g_fMARGIN && v <= 1. + g_fMARGIN && u + v <= 1. + g_fMARGIN)
      {
        return true;
      }
    }
    //else
    u = -1.; v = -1.; w = -1.;
    return false;
  }


  void  inline QuickSort(SLOT_BUFFER_TYPE A[], size_t I[], size_t lo, size_t hi)
  {//https://stackoverflow.com/questions/55976487/get-the-sorted-indices-of-an-array-using-quicksort
    while (lo < hi)
    {
      SLOT_BUFFER_TYPE pivot = A[I[lo + (hi - lo) / 2]];
      size_t t;
      size_t i = lo - 1;
      size_t j = hi + 1;
      while (1)
      {
        while (A[I[++i]] < pivot);
        while (A[I[--j]] > pivot);
        if (i >= j)
          break;
        t = I[i];
        I[i] = I[j];
        I[j] = t;
      }
      /* avoid stack overflow */
      if ((j - lo) < (hi - j)) {
        QuickSort(A, I, lo, j);
        lo = j + 1;
      }
      else {
        QuickSort(A, I, j + 1, hi);
        hi = j;
      }
    }
  }

  void  inline uintTo32Bools(BIT_BUFFER_TYPE _byte, bool _bBits[8])
  {
    for (int i = 0; i < 32; i++)
    {
      _bBits[i] = _byte & (1 << (31 - i));//순서 맞나?
    }
  }

  SLOT_BUFFER_TYPE  inline toTypeByte(enumPixelType type)
  {
    return SLOT_BUFFER_TYPE(1 << static_cast<SLOT_BUFFER_TYPE>(type));
  }

  std::chrono::steady_clock::time_point begin, end;

  void  startTimer(void)
  {
    begin = std::chrono::steady_clock::now();
  }

  void  endTimer(const char* title)
  {
    end = std::chrono::steady_clock::now();
    if(title!=nullptr) std::cout << title;
    int micro_sec = std::chrono::duration_cast<std::chrono::microseconds>(end - begin).count();
    std::cout << " time = " << micro_sec *0.001 << "[ms] = " << micro_sec << "[us]" << std::endl;
  }
  FLOAT32  getDist3D(FLOAT32* a, FLOAT32* b)
  {
    FLOAT32 temp = (a[0] - b[0]) * (a[0] - b[0]);
    temp += (a[1] - b[1]) * (a[1] - b[1]);
    temp += (a[2] - b[2]) * (a[2] - b[2]);

    if (temp < 0) { return 0; }
    return sqrt(temp);
  }


  FLOAT32   getTriArea3D(FLOAT32* a, FLOAT32* b, FLOAT32* c)
  {
    FLOAT32 area = 0, s, l_a, l_b, l_c;
    l_a = Tomo::getDist3D(b, c);
    l_b = Tomo::getDist3D(a, c);
    l_c = Tomo::getDist3D(a, b);
    s = (l_a + l_b + l_c) / 2;
    area = s * (s - l_a) * (s - l_b) * (s - l_c);
    area = (area > 0) ? ::sqrt(area) : ::sqrt(-area);
    return area;
  }
}