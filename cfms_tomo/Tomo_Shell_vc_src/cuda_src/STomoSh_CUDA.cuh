#include "../cpu_src/STomoSh_Base.h" 
#include "CUDA_types.cuh"
#include "SlotData.cuh"

using namespace Tomo;

typedef int* INTP;
typedef float* FLOATP;


//This class uses multiple CUDA streams.

class  STomoSh_CUDA : public STomoSh_Base
{
public:
  //derived from STomoSh_Base class
  __host__ STomoSh_CUDA();
  __host__ STomoSh_CUDA(const STomoSh_CUDA& Source);
  __host__ void	operator=(const STomoSh_CUDA& Source);
  __host__ void	_Copy(const STomoSh_CUDA& Source);
  __host__ ~STomoSh_CUDA();

  __host__ void	Reset(void);
  __host__ void	Init(void);

  //derived from STomoSh_CUDA0 class
    __host__ void	Init_CUDA(void);
      __host__  void  initCudaMem(void);
      __host__  void  clearCudaMem(void);
      __host__ void	getBatchNumber(void);//get number of streams to use.

  __host__ void	Run(float *_Mo, float *_Mss, int ypr_id_to_start = 0);

    __host__ void  Step1_RotateAndPixelize(SlotDataIterator, int yprID_to_start);
      __host__ void  Step1_TruncateSlots(SlotDataIterator);//keep CU_SLOT_TRUNCATE_TO largest keys per slot (CPU-capacity regime)

    __host__ void  Step2_Pairing(SlotDataIterator);

    __host__ void  Step3_GenerateBed(SlotDataIterator);

    __host__ void	 Step4_SlotSum_Batch(int yprID, float *_Mo, float *_Mss); 
      __host__ void	 Step4_SlotSum( SlotDataIterator, int *_cu_reduced_sum_buffer,  int *_reduced_sum_buffer, float *_Mo, float *_Mss); 
    
  __host__ FLOAT32* ReadPxls(int _yprID, int* _nData2i, INT16** _pData2i);

  static const size_t niData = 21+1;// + bInputMeshNotClosed
  static const size_t siData = sizeof(size_t) * niData;
  union
  {
    struct 
    { 
      //params
      size_t nFlatTri;
      size_t nVoxelX,nVoxelY;//= fixed at 256 x 256.
      size_t nSlot;//=nVoxelX * nVoxelY = 255 * 255 = 65,536
      size_t nYPR;
      size_t nSlotData;

      size_t nWorksInBatch;//actual number of YPR's to process at a time

      //data size
      size_t  s_nSlot;
      size_t  s_nSlotData;
      size_t  s_nFlatTri;

      size_t  s_m4x3;
      size_t  gpu_available_mem;
      size_t  gpu_total_mem;

      //device property
      size_t  nMultiProcessor;//==6 for GTX760, 128 for RTX 4090.
      size_t  nMaxThreadPerMP;//==1024 for GTX760

      size_t  nMaxThreads;// = nMultiProcessor * nMaxThreadPerMP = 12,288 for GTX760
      size_t  nMaxConcurrentStream;//max number of streams. == 16 for GTX760
      size_t  nStream;//actual number of streams to use concurrently. <= nMaxConcurrentStream 

      size_t  bShellMesh;//obsolete..
      size_t  bInputMeshNotClosed;//obsolete..
    };
    size_t iData[niData];
  };

  //Slot data
  SlotData  cpu_SlotData;
  std::vector<SlotData> gpu_SlotDataVec;

  static const int cu_nfpData = 5;
  static const int cu_sfpData = sizeof(FLOATP) * cu_nfpData;
  union
  {
    struct
    {
      FLOATP cu_FlatTri0;//input triangle data from CPU [nTri * nFlatTriInfoSize]
#ifndef _CUDA_USE_ROTATE_AND_PIXELIZE_IN_ONE_STEP
      FLOATP cu_FlatTri1;//triangle data after rotation. [(nTri * nFlatTriInfoSize) * nYPR]. for debug.
#endif
      FLOATP  cu_m4x3;//rotation + trnslation matrix. [nYPR * 4*4] 
      FLOATP  ho_CVVoxels, cu_CVVoxels;//obsolete..
    };
    FLOATP cu_fpData[cu_nfpData];
  };

  bool bWriteBackPxlsForRendering;
  int *cu_sum_buffer, *sum_buffer;
  int *cu_parentHit;
  float *cu_parentFallbackTri;
  int *cu_Tri0;
  float *cu_Vtx0, *cu_VtxNrm0;
  #ifdef _CUDA_USE_SERIALIZED_VO_VSS_MEMORY
  void	 __Malloc_Serialized_Vo_Vss_memory(void);
  void	 __Free_Serialized_Vo_Vss_memory(void);
  #endif

};
