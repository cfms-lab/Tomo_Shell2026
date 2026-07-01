#pragma once
#include "../Tomo_types.h"

using namespace Tomo;

class	DLLEXPORT SMatrix4f {
public:
	SMatrix4f(FLOAT32 yaw = 0., FLOAT32 pitch = 0., FLOAT32 roll = 0.);
	SMatrix4f(const SMatrix4f& Source);
	void	operator=(const SMatrix4f& Source);
	void	_Copy(const SMatrix4f& Source);
	~SMatrix4f();

	void	Reset(void);
	void	Init(void);


	static const int nRow = 3;
	static const int nCol = 3;

	static const int nfData = nRow*nCol;
	static const int sfData = sizeof(FLOAT32) * nfData;
	union
	{
		FLOAT32 Data[nRow][nCol];
		FLOAT32 fData[nRow*nCol];
	};
	;
	SMatrix4f&	Identity(void);
	SMatrix4f&	OuterProduct( FLOAT32 *a, FLOAT32 *b);//3d vector

	SMatrix4f	  operator+(const SMatrix4f&	a) const;
	SMatrix4f	  operator-(const SMatrix4f&	a) const;
	SMatrix4f&  operator+=(const SMatrix4f&);
	SMatrix4f&  operator-=(const SMatrix4f&);

	SMatrix4f operator*(FLOAT32);

	void		T(SMatrix4f& a);//transpose

	void		AXPY( FLOAT32 alpha, const SMatrix4f& a, FLOAT32 a_factor =1.);
	void		AXPY( FLOAT32 a, FLOAT32 *x, FLOAT32 b);//UpperDiagonalJacobian¿ë
	void	  AddProduct( FLOAT32 alpha, FLOAT32 beta, const SMatrix4f& a, const SMatrix4f& b);

	void  Dot(FLOAT32* a, FLOAT32* result);
	void    YPR(FLOAT32 yaw, FLOAT32 pitch, FLOAT32 roll);

};

SMatrix4f operator*(FLOAT32,SMatrix4f const&);
