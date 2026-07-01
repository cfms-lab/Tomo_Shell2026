#pragma once
#include "../Tomo_types.h"
#include "CUDA_types.cuh"
#include <vector>

using namespace Tomo;

class DLLEXPORT SlotData
{
public:
	SlotData();
	SlotData(const SlotData& Source);
	void	operator=(const SlotData& Source);
	void	_Copy(const SlotData& Source);
	~SlotData();

	void	Reset(void);
	void	Init(void);

	void	Malloc(int _nSlot);
	void  Free(void);

	bool	bDevice;//true=GPU, false=CPU

	static const int n_uliData = 4;
	static const int s_uliData = sizeof(CU_ULInt) * n_uliData;
	union
	{
		struct 
		{ 
			//params
			CU_ULInt nSlot, nSlotData;
			CU_ULInt s_nSlot, s_nSlotData;
		};			
		CU_ULInt uliData[n_uliData];
	};

	//GPU memory. 
	static const int n_sbpData = 7;
	static const int s_sbpData = sizeof(CU_SLOT_BUFFER_TYPE*) * n_sbpData;
	union
	{
		struct
		{
			CU_SLOT_BUFFER_TYPE* cu_sNPxl;//number of pxles in slot (X,Y)
			CU_SLOT_BUFFER_TYPE* cu_sVo;//pixel volume
			CU_SLOT_BUFFER_TYPE* cu_sVss;//pixel support structure volume

			CU_SLOT_BUFFER_TYPE* cu_sdType;//type of pixel
			CU_SLOT_BUFFER_TYPE* cu_sdZcrd;///Z coordinate of pixel
			CU_SLOT_BUFFER_TYPE* cu_sdZnrm;//normal vector's Z-component of pixel

			CU_SLOT_BUFFER_TYPE* cu_ReducedSum_Buffer;//4 byte
		};
		CU_SLOT_BUFFER_TYPE* sbpData[n_sbpData];
	};

	void	ReadPxls(
		CU_SLOT_BUFFER_TYPE* nPixel,
		CU_SLOT_BUFFER_TYPE* pType,
		CU_SLOT_BUFFER_TYPE* pZcrd,
		CU_SLOT_BUFFER_TYPE* pZnrm);

	void	SetZero(void);

	//stream
	cudaStream_t	stream;
	cudaEvent_t		event;
	
	#ifdef _CUDA_USE_REDUCED_SUM_BATCH
	cudaStream_t Vo_stream, Vss_stream;
	cudaEvent_t		Vo_event, Vss_event;
	#endif

	void	CreateStream(void);
	void	DestroyStream(void);

};

typedef std::vector<SlotData> SlotDataVector;
typedef SlotDataVector::iterator SlotDataIterator;

