#include "matrix4.h"
#include <cstring>

namespace math {

Matrix4::Matrix4() {
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            m[i][j] = (i == j) ? 1.0 : 0.0;
}

Matrix4 Matrix4::identity() { return Matrix4(); }

Matrix4 Matrix4::translation(const Vec3& t) {
    Matrix4 mat;
    mat.m[0][3] = t.x;
    mat.m[1][3] = t.y;
    mat.m[2][3] = t.z;
    return mat;
}

Matrix4 Matrix4::rotation(double angle, const Vec3& axis) {
    Matrix4 mat;
    double c = std::cos(angle);
    double s = std::sin(angle);
    double t = 1.0 - c;
    Vec3 a = axis.normalized();

    mat.m[0][0] = t * a.x * a.x + c;
    mat.m[0][1] = t * a.x * a.y - s * a.z;
    mat.m[0][2] = t * a.x * a.z + s * a.y;
    mat.m[1][0] = t * a.x * a.y + s * a.z;
    mat.m[1][1] = t * a.y * a.y + c;
    mat.m[1][2] = t * a.y * a.z - s * a.x;
    mat.m[2][0] = t * a.x * a.z - s * a.y;
    mat.m[2][1] = t * a.y * a.z + s * a.x;
    mat.m[2][2] = t * a.z * a.z + c;
    return mat;
}

Matrix4 Matrix4::scaling(const Vec3& s) {
    Matrix4 mat;
    mat.m[0][0] = s.x;
    mat.m[1][1] = s.y;
    mat.m[2][2] = s.z;
    return mat;
}

Matrix4 Matrix4::perspective(double fov, double aspect, double nearPlane, double farPlane) {
    Matrix4 mat;
    double tanHalfFov = std::tan(fov * 0.5);
    mat.m[0][0] = 1.0 / (aspect * tanHalfFov);
    mat.m[1][1] = 1.0 / tanHalfFov;
    mat.m[2][2] = -(farPlane + nearPlane) / (farPlane - nearPlane);
    mat.m[2][3] = -(2.0 * farPlane * nearPlane) / (farPlane - nearPlane);
    mat.m[3][2] = -1.0;
    mat.m[3][3] = 0.0;
    return mat;
}

Matrix4 Matrix4::lookAt(const Vec3& eye, const Vec3& target, const Vec3& up) {
    Vec3 f = (target - eye).normalized();
    Vec3 s = f.cross(up.normalized()).normalized();
    Vec3 u = s.cross(f);

    Matrix4 mat;
    mat.m[0][0] = s.x;  mat.m[0][1] = s.y;  mat.m[0][2] = s.z;
    mat.m[1][0] = u.x;  mat.m[1][1] = u.y;  mat.m[1][2] = u.z;
    mat.m[2][0] = -f.x; mat.m[2][1] = -f.y; mat.m[2][2] = -f.z;
    mat.m[0][3] = -s.dot(eye);
    mat.m[1][3] = -u.dot(eye);
    mat.m[2][3] = f.dot(eye);
    return mat;
}

Matrix4 Matrix4::operator*(const Matrix4& other) const {
    Matrix4 result;
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j) {
            result.m[i][j] = 0;
            for (int k = 0; k < 4; ++k)
                result.m[i][j] += m[i][k] * other.m[k][j];
        }
    return result;
}

Vec3 Matrix4::transformPoint(const Vec3& p) const {
    double w = m[3][0] * p.x + m[3][1] * p.y + m[3][2] * p.z + m[3][3];
    return Vec3(
        (m[0][0] * p.x + m[0][1] * p.y + m[0][2] * p.z + m[0][3]) / w,
        (m[1][0] * p.x + m[1][1] * p.y + m[1][2] * p.z + m[1][3]) / w,
        (m[2][0] * p.x + m[2][1] * p.y + m[2][2] * p.z + m[2][3]) / w
    );
}

Vec3 Matrix4::transformDirection(const Vec3& d) const {
    return Vec3(
        m[0][0] * d.x + m[0][1] * d.y + m[0][2] * d.z,
        m[1][0] * d.x + m[1][1] * d.y + m[1][2] * d.z,
        m[2][0] * d.x + m[2][1] * d.y + m[2][2] * d.z
    );
}

Matrix4 Matrix4::transposed() const {
    Matrix4 result;
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            result.m[i][j] = m[j][i];
    return result;
}

} // namespace math
