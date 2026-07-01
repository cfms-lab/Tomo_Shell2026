#pragma once
#include "../Tomo_types.h"

using namespace Tomo;

class	DLLEXPORT SMatrix33f {
public:
	SMatrix33f(FLOAT32 yaw = 0., FLOAT32 pitch = 0., FLOAT32 roll = 0.);
	SMatrix33f(const SMatrix33f& Source);
	void	operator=(const SMatrix33f& Source);
	void	_Copy(const SMatrix33f& Source);
	~SMatrix33f();

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
	SMatrix33f&	Identity(void);
	SMatrix33f&	OuterProduct( FLOAT32 *a, FLOAT32 *b);//3d vector

	SMatrix33f	  operator+(const SMatrix33f&	a) const;
	SMatrix33f	  operator-(const SMatrix33f&	a) const;
	SMatrix33f&  operator+=(const SMatrix33f&);
	SMatrix33f&  operator-=(const SMatrix33f&);

	SMatrix33f operator*(FLOAT32);

	void		T(SMatrix33f& a);//transpose

	void		AXPY( FLOAT32 alpha, const SMatrix33f& a, FLOAT32 a_factor =1.);
	void		AXPY( FLOAT32 a, FLOAT32 *x, FLOAT32 b);//UpperDiagonalJacobian¿ë
	void	  AddProduct( FLOAT32 alpha, FLOAT32 beta, const SMatrix33f& a, const SMatrix33f& b);

	void  Dot(FLOAT32* a, FLOAT32* result);
	void    YPR(FLOAT32 yaw, FLOAT32 pitch, FLOAT32 roll);

};

SMatrix33f operator*(FLOAT32,SMatrix33f const&);
