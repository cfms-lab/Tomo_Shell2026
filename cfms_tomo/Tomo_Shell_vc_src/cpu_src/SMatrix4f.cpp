#include "pch.h"
#include "SMatrix4f.h"
#include <cstring> //memcpy()
#include <math.h>

using namespace Tomo;

SMatrix4f::SMatrix4f(FLOAT32 yaw, FLOAT32 pitch, FLOAT32 roll)
{
	Init();
	YPR(yaw, pitch, roll);
}

SMatrix4f::~SMatrix4f()
{
	Reset();
}

SMatrix4f::SMatrix4f(const SMatrix4f& Source)
{
	Init();
	_Copy(Source);
}

void	SMatrix4f::operator=(const SMatrix4f& Source)
{
	Reset();
	_Copy(Source);
}

void	SMatrix4f::_Copy(const SMatrix4f& Source)
{
	memcpy(fData, Source.fData, sfData);
}

void	SMatrix4f::Reset(void)
{
	Init();
}

void	SMatrix4f::Init(void)
{
	memset(fData, 0x00, sfData);
}

//-------------------------------------------------
SMatrix4f& SMatrix4f::Identity(void)
{
	Reset();
	Data[0][0] = 1.;
	Data[1][1] = 1.;
	Data[2][2] = 1.;

	return *this;
}

SMatrix4f& SMatrix4f::OuterProduct( FLOAT32 *a, FLOAT32 *b)
{
	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			Data[i][j] = a[i] * b[j];
		}
	}

	return *this;
}

SMatrix4f	SMatrix4f::operator+(const SMatrix4f&	a) const
{
	SMatrix4f temp;

	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			temp.Data[i][j] = Data[i][j] + a.Data[i][j];
		}
	}

	return temp;
}

SMatrix4f	SMatrix4f::operator-(const SMatrix4f&	a) const
{
	SMatrix4f temp;

	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			temp.Data[i][j] = Data[i][j] - a.Data[i][j];
		}
	}

	return temp;
}

SMatrix4f& SMatrix4f::operator+=(const SMatrix4f& a)
{
	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			Data[i][j] += Data[i][j];
		}
	}

	return *this;
}

SMatrix4f& SMatrix4f::operator-=(const SMatrix4f& a)
{
	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			Data[i][j] -= a.Data[i][j];
		}
	}

	return *this;
}

SMatrix4f SMatrix4f::operator*(FLOAT32 b)
{
	SMatrix4f temp;

	for(int i = 0 ; i < nCol ; i++)
	{
		for( int j = 0 ; j < nRow ; j++)
		{
			temp.Data[i][j] = Data[i][j] * b;
		}
	}

	return temp;
}

SMatrix4f operator*(FLOAT32 b,SMatrix4f const & m)
{
	SMatrix4f temp;

	for(int i = 0 ; i < m.nCol ; i++)
	{
		for( int j = 0 ; j < m.nRow ; j++)
		{
			temp.Data[i][j] = m.Data[i][j] * b;
		}
	}

	return temp;
}


void		SMatrix4f::T(SMatrix4f& a)
{
	int i,j;
	for( i = 0 ; i < a.nCol ; i++)
	{
		for( j = 0 ; j < a.nRow ; j++)
		{
			Data[i][j] = a.Data[j][i];
		}
	}
}

void		SMatrix4f::AXPY( FLOAT32 alpha, const SMatrix4f& a, FLOAT32 a_factor)
{
	int i,j;
	for( i = 0 ; i < nCol ; i++)
	{
		for( j = 0 ; j < nRow ; j++)
		{
			Data[i][j] = Data[i][j] * alpha + a.Data[i][j] * a_factor;
		}
	}
}

	
void		SMatrix4f::AXPY( FLOAT32 a, FLOAT32*x, FLOAT32 b)
{//UpperDiagonalJacobian��
	int i,j;
	for( i = 0 ; i < nCol ; i++)
	{
		for( j = 0 ; j < nRow ; j++)
		{
			Data[i][j] += a * x[i*nCol+j] + b;
		}
	}

}

void	  SMatrix4f::AddProduct( FLOAT32 alpha, FLOAT32 beta, const SMatrix4f& a, const SMatrix4f& b)
{
	int i,j,k;
	FLOAT32 sum;
	for( i = 0 ; i < nCol ; i++)
	{
		sum = 0;
		for( j = 0 ; j < nRow ; j++)
		{
			for( k = 0 ; k < nRow ; k++)
			{
				sum += a.Data[i][k] * b.Data[k][j];
			}
			Data[i][j] = alpha * Data[i][j] + beta * sum;
		}
	}
}

void    SMatrix4f::YPR(FLOAT32 ga, FLOAT32 be, FLOAT32 al)//�� ���� roll * pitch * yaw �����ε�, ���̽� ������ ���߱� ���� al, ga������ �ٲ� ��. 
{//http://planning.cs.uiuc.edu/node102.html
	 
	FLOAT32 cos_al = ::cos(al);
	FLOAT32 cos_be = ::cos(be);
	FLOAT32 cos_ga = ::cos(ga);

	FLOAT32 sin_al = ::sin(al);
	FLOAT32 sin_be = ::sin(be);
	FLOAT32 sin_ga = ::sin(ga);

	Data[0][0] = cos_al * cos_be;
	Data[0][1] = cos_al * sin_be * sin_ga - sin_al*  cos_ga;
	Data[0][2] = cos_al * sin_be * cos_ga + sin_al * sin_ga;

	Data[1][0] = sin_al * cos_be;
	Data[1][1] = sin_al * sin_be * sin_ga + cos_al * cos_ga;
	Data[1][2] = sin_al * sin_be * cos_ga - cos_al * sin_ga;

	Data[2][0] = - sin_be;
	Data[2][1] = cos_be * sin_ga;
	Data[2][2] = cos_be * cos_ga;

	//homogeneous coordniate
	Data[3][3] = 1.;


}

void  SMatrix4f::Dot(FLOAT32* a, FLOAT32* result)
{
	FLOAT32 temp[nCol] = { a[0], a[1], a[2], 1. };//add homogeneous coordinate.

	result[0]  = Data[0][0] * temp[0];
	result[0] += Data[0][1] * temp[1];
	result[0] += Data[0][2] * temp[2];
	result[0] += Data[0][3] * temp[3];

	result[1]  = Data[1][0] * temp[0];
	result[1] += Data[1][1] * temp[1];
	result[1] += Data[1][2] * temp[2];
	result[1] += Data[1][3] * temp[3];

	result[2]  = Data[2][0] * temp[0];
	result[2] += Data[2][1] * temp[1];
	result[2] += Data[2][2] * temp[2];
	result[2] += Data[2][3] * temp[3];

	//result[3] calculation is not neeed (affine transform).
}


