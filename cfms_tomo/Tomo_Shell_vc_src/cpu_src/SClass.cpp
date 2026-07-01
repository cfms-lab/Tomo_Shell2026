#include "pch.h"
#include "SClass.h"

SClass::SClass()
{
	Init();
}

SClass::~SClass()
{
	Reset();
}

SClass::SClass(const SClass& Source)
{
	Init();
	_Copy(Source);
}

void	SClass::operator=(const SClass& Source)
{
	Reset();
	_Copy(Source);
}

void	SClass::_Copy(const SClass& Source)
{
	memcpy(iData, Source.iData, siData);
}

void	SClass::Reset(void)
{
	Init();
}

void	SClass::Init(void)
{
	memset( iData, 0x00, siData);
}

//---------------------- obsolete,
#include <iomanip> 
void	_debugPrintMss(float *_Mss, int nYPR, int step)
{
#ifdef _DEBUG
	if(nYPR==1) return;
	int nYaw = int(sqrt(nYPR));
	int nPitch = nYaw;
	int _ypr_id = 0;
	std::cout << "[ " << std::fixed << std::setw(2) << std::setprecision(2) << std::setfill('0') ;//debug
	for( int y= 0 ; y < nYaw; y++)
	{
		std::cout << "[ " ;
		for(int p = 0 ; p < nPitch; p++)
		{
			std::cout << _Mss[ _ypr_id++] << " ";
			if(_ypr_id% step == 0) std::cout << "/";
		}
		std::cout << " ]" << std::endl;	
	 }
	 std::cout << std::endl << std::endl;
#endif
}

#if 0
__host__ void STomoNV_CUDA0::getCuda2DArray(CU_INTPP pointer, int row, int col)
{
	cudaMalloc((void **)&pointer,col*sizeof(int*));
	for(int i = 0 ; i < col ; i++)
	{
		cudaMalloc(&(pointer[i]),row*sizeof(int));	
	}
	cudaCheckError();
}

__host__ void STomoNV_CUDA0::getCuda2DArray(CU_FLOATPP pointer, int row, int col)
{
	cudaMalloc((void **)&pointer,col*sizeof(float*));
	for(int i = 0 ; i < col ; i++)
	{
		cudaMalloc((void **)&pointer[i],row*sizeof(float));	
	}
}
#endif




#ifdef _CUDA_USE_MULTI_STREAM

nYPRInStream = int(nYPRInBatch / nStream) + 0;

	//multi-stream 
	
	cudaStream_t *streams;
	if(nYPR > 1)
	{
		streams = new cudaStream_t[nStream];//GTX 760은 스트림 최대 16개밖에 안됨.
		for (int s = 0; s < nStream; s++)
		{
			cudaStreamCreate(&streams[s]);
			cudaStreamCreateWithFlags(&streams[s],cudaStreamNonBlocking);
		}

		int nBatch = nYPR / nStream * nYPRInStream;
		int nBatchRest = nYPR % (nStream * nYPRInStream);

		for( int b = 0 ; b < nBatch ; b++)//너무 느리다..
		{
			for (int s = 0; s < nStream; s++)
			{
				RotateAndPixelize(		nYPRInStream, nYPRInStream * (nStream * b + s), streams[s]);
			}
		}
		for (int s = 0; s < nStream; s++)		cudaStreamSynchronize(streams[s]);

		//for (int s = 0; s < nStream; s++)
		//{
		//	Pairing(	nYPRInStream, streams[s]);
		//}
		//for (int s = 0; s < nStream; s++)		cudaStreamSynchronize(streams[s]);

		//for (int s = 0; s < nStream; s++)		
		//{
		//	Calculate(nYPRInStream, _Mo + nYPRInStream * s, _Mss + nYPRInStream * s, streams[s]);
		//}
		//for (int s = 0; s < nStream; s++)		cudaStreamSynchronize(streams[s]);

		yprID_to_start += nBatch * nYPRInStream * nStream;

		//the rest iteration
		RotateAndPixelize( nBatchRest, yprID_to_start);
		Pairing(	nBatchRest);
		Calculate(nBatchRest,	 _Mo + yprID_to_start, _Mss + yprID_to_start);
		yprID_to_start += nBatchRest;

	}

if(nYPR>1) for (int s = 0; s < nStream; s++)		 cudaStreamDestroy(streams[s]);
#else