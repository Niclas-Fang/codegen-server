#pragma once
#include "vec3.h"

namespace math {

class Matrix4 {
public:
    double m[4][4];

    Matrix4();
    static Matrix4 identity();
    static Matrix4 translation(const Vec3& t);
    static Matrix4 rotation(double angle, const Vec3& axis);
    static Matrix4 scaling(const Vec3& s);
    static Matrix4 perspective(double fov, double aspect, double nearPlane, double farPlane);
    static Matrix4 lookAt(const Vec3& eye, const Vec3& target, const Vec3& up);
    static Matrix4 fromAxes(const Vec3& xAxis, const Vec3& yAxis, const Vec3& zAxis);

    Matrix4 operator*(const Matrix4& other) const;
    Matrix4& operator*=(const Matrix4& other);

    Vec3 transformPoint(const Vec3& p) const;
    Vec3 transformDirection(const Vec3& d) const;
    Vec3 transformVector(const Vec3& v) const;

    Matrix4 transposed() const;
    Matrix4 inverted() const;
    Matrix4 invertedFast() const;

    double determinant() const;
    double trace() const;

    void decompose(Vec3& translation, Vec3& rotation, Vec3& scale) const;

    double* data() { return &m[0][0]; }
    const double* data() const { return &m[0][0]; }
};

} // namespace math
