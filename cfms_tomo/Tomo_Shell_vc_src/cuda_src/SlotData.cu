#include "SlotData.cuh"

using namespace Tomo;

SlotData::SlotData()
{
	Init();
}

SlotData::~SlotData()
{
	Reset();
}

SlotData::SlotData(const SlotData& Source)
{
	Init();
	_Copy(Source);
}

void	SlotData::operator=(const SlotData& Source)
{
	Reset();
	_Copy(Source);
}

void	SlotData::_Copy(const SlotData& Source)
{
	memcpy(uliData, Source.uliData, s_uliData);//params.
	memcpy(sbpData, Source.sbpData, s_sbpData);//GPU mem
	stream = Source.stream;
	event = Source.event;

	#ifdef _CUDA_USE_REDUCED_SUM_BATCH
	Vo_stream = Source.Vo_stream;
	Vss_stream = Source.Vss_stream;
	Vo_event = Source.Vo_event;
	Vss_event = Source.Vss_event;
	#endif

}

void	SlotData::Reset(void)
{
	Init();
}

void	SlotData::Init(void)
{
	memset(uliData, 0x00, s_uliData);//params.
	memset(sbpData, 0x00, s_sbpData);//GPU mem
	bDevice = true;
	stream = 0;
	event = 0;

	#ifdef _CUDA_USE_REDUCED_SUM_BATCH
	Vo_stream = 0;
	Vss_stream = 0;
	Vo_event = 0;
	Vss_event = 0;
	#endif
}


void	SlotData::Malloc(int _nSlot)
{
	nSlot = _nSlot;
	nSlotData	= _nSlot * CU_SLOT_CAPACITY_16;

	s_nSlot			= sizeof(CU_SLOT_BUFFER_TYPE) * nSlot;
	s_nSlotData	= sizeof(CU_SLOT_BUFFER_TYPE) * nSlotData;

	//GPU memory - as 1D
	if(bDevice)
	{
		#ifdef _CUDA_USE_SERIALIZED_SLOTDATA_MEMORY
		CU_SLOT_BUFFER_TYPE *cu_buf = 0;
		const size_t s_serial_data = s_nSlot + s_nSlotData * 3 + 2 * sizeof(CU_SLOT_BUFFER_TYPE);
		cudaMalloc( (void**)&cu_buf,	s_serial_data);	cudaCheckError();
		cu_sNPxl	= cu_buf;
		cu_sdType = cu_sNPxl + nSlot;
		cu_sdZcrd = cu_sdType + nSlotData;
		cu_sdZnrm = cu_sdZcrd + nSlotData;
		cu_ReducedSum_Buffer = cu_sdZnrm + nSlotData;
		#else
		cudaMalloc((void**)&cu_sNPxl,		s_nSlot);				cudaCheckError();
		cudaMalloc((void**)&cu_sdType,	s_nSlotData);		cudaCheckError();
		cudaMalloc((void**)&cu_sdZcrd,	s_nSlotData);		cudaCheckError();
		cudaMalloc((void**)&cu_sdZnrm,	s_nSlotData);		cudaCheckError();
		cudaMalloc((void**)&cu_ReducedSum_Buffer,				sizeof(CU_SLOT_BUFFER_TYPE) * 2);	cudaCheckError();
		#endif

		cudaMalloc((void**)&cu_sVo,			s_nSlot);				cudaCheckError();
		cudaMalloc((void**)&cu_sVss,		s_nSlot);				cudaCheckError();

	}
	else
	{
		cudaMallocHost((void**)&cu_sNPxl,		s_nSlot);				cudaCheckError();
	
		cudaMallocHost((void**)&cu_sdType,	s_nSlotData);		cudaCheckError();
		cudaMallocHost((void**)&cu_sdZcrd,	s_nSlotData);		cudaCheckError();
		cudaMallocHost((void**)&cu_sdZnrm,	s_nSlotData);		cudaCheckError();

		cudaMallocHost((void**)&cu_ReducedSum_Buffer,				sizeof(CU_SLOT_BUFFER_TYPE) * 2);	cudaCheckError();

		cudaMallocHost((void**)&cu_sVo,			s_nSlot);				cudaCheckError();
		cudaMallocHost((void**)&cu_sVss,		s_nSlot);				cudaCheckError();
	}

}

void	SlotData::Free(void)
{
	if(bDevice)
	{
		#ifdef _CUDA_USE_SERIALIZED_SLOTDATA_MEMORY
		cudaFree((void*)cu_sNPxl);		cudaCheckError();
		cu_sNPxl = cu_sdType = cu_sdZcrd = cu_sdZnrm = cu_ReducedSum_Buffer = nullptr;
		#else
		cudaFree((void*)cu_sNPxl);	cudaCheckError();
		cudaFree((void*)cu_sdType);	cudaCheckError();
		cudaFree((void*)cu_sdZcrd);	cudaCheckError();
		cudaFree((void*)cu_sdZnrm);	cudaCheckError();
		cudaFree((void*)cu_ReducedSum_Buffer);cudaCheckError();
		#endif


		cudaFree((void*)cu_sVo);		cudaCheckError();
		cudaFree((void*)cu_sVss);		cudaCheckError();
	 }
	else
	{
		cudaFreeHost((void*)cu_sNPxl);	cudaCheckError();
		cudaFreeHost((void*)cu_sVo);		cudaCheckError();
		cudaFreeHost((void*)cu_sVss);		cudaCheckError();
		cudaFreeHost((void*)cu_sdType);	cudaCheckError();
		cudaFreeHost((void*)cu_sdZcrd);	cudaCheckError();
		cudaFreeHost((void*)cu_sdZnrm);	cudaCheckError();
		cudaFreeHost((void*)cu_ReducedSum_Buffer);cudaCheckError();
	}
}

void	SlotData::ReadPxls(
	CU_SLOT_BUFFER_TYPE* nPixel,
	CU_SLOT_BUFFER_TYPE* pType,
	CU_SLOT_BUFFER_TYPE* pZcrd,
	CU_SLOT_BUFFER_TYPE* pZnrm)
{
	cudaMemcpy(nPixel,	(void*)cu_sNPxl,			s_nSlot, cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pType,		(void*)cu_sdType,	s_nSlotData, cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZcrd,		(void*)cu_sdZcrd,	s_nSlotData, cudaMemcpyDeviceToHost);  cudaCheckError();
	cudaMemcpy(pZnrm,		(void*)cu_sdZnrm,	s_nSlotData, cudaMemcpyDeviceToHost);  cudaCheckError();
	
}

void	SlotData::SetZero(void)
{
	#ifdef _CUDA_USE_SERIALIZED_SLOTDATA_MEMORY
	const size_t s_serial_data = s_nSlot + s_nSlotData * 3 + 2 * sizeof(CU_SLOT_BUFFER_TYPE);
	cudaMemsetAsync((void*)cu_sNPxl,		0x00, s_serial_data,		 stream);					cudaCheckError();
	#else
	cudaMemsetAsync((void*)cu_sNPxl,		0x00, s_nSlot,		 stream);					cudaCheckError();
	cudaMemsetAsync((void*)cu_sdType,		0x00, s_nSlotData, stream);					cudaCheckError();
	cudaMemsetAsync((void*)cu_sdZcrd,		0x00, s_nSlotData, stream);					cudaCheckError();
	cudaMemsetAsync((void*)cu_sdZnrm,		0x00, s_nSlotData, stream);					cudaCheckError();
	#endif

#ifndef _CUDA_USE_SERIALIZED_VO_VSS_MEMORY
	cudaMemsetAsync((void*)cu_sVo,			0x00, s_nSlot,		 stream);					cudaCheckError();
	cudaMemsetAsync((void*)cu_sVss,			0x00, s_nSlot,		 stream);					cudaCheckError();
#endif
}

void	SlotData::CreateStream(void)
{
	cudaStreamCreateWithFlags(	&stream,	cudaStreamNonBlocking); cudaCheckError();
	cudaEventCreate(&event); cudaCheckError();

#ifdef _CUDA_USE_REDUCED_SUM_BATCH
	cudaStreamCreateWithFlags(	&Vo_stream,	cudaStreamNonBlocking); cudaCheckError();
	cudaStreamCreateWithFlags(	&Vss_stream,	cudaStreamNonBlocking); cudaCheckError();
	cudaEventCreate(&Vo_event);cudaCheckError();	
	cudaEventCreate(&Vss_event);cudaCheckError();	
#endif
}

void	SlotData::DestroyStream(void)
{
	cudaEventDestroy(event);   cudaCheckError();
	cudaStreamDestroy(stream); cudaCheckError();

	#ifdef _CUDA_USE_REDUCED_SUM_BATCH
	cudaEventDestroy(Vo_event);   cudaCheckError();
	cudaEventDestroy(Vss_event);   cudaCheckError();
	cudaStreamDestroy(Vo_stream); cudaCheckError();
	cudaStreamDestroy(Vss_stream); cudaCheckError();
	#endif

}
