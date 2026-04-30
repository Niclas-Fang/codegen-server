#pragma once
#include <cmath>

namespace math {

class Vec3 {
public:
    double x, y, z;

    Vec3(double x = 0, double y = 0, double z = 0) : x(x), y(y), z(z) {}

    Vec3 operator+(const Vec3& other) const { return Vec3(x + other.x, y + other.y, z + other.z); }
    Vec3 operator-(const Vec3& other) const { return Vec3(x - other.x, y - other.y, z - other.z); }
    Vec3 operator*(double scalar) const { return Vec3(x * scalar, y * scalar, z * scalar); }
    Vec3 operator/(double scalar) const { return Vec3(x / scalar, y / scalar, z / scalar); }

    double dot(const Vec3& other) const { return x * other.x + y * other.y + z * other.z; }
    Vec3 cross(const Vec3& other) const;
    double length() const { return std::sqrt(x*x + y*y + z*z); }
    double lengthSquared() const { return x*x + y*y + z*z; }
    Vec3 normalized() const;

    double operator[](int i) const { return i == 0 ? x : (i == 1 ? y : z); }
    double& operator[](int i) { return i == 0 ? x : (i == 1 ? y : z); }

    static Vec3 zero() { return Vec3(0, 0, 0); }
    static Vec3 one() { return Vec3(1, 1, 1); }
    static Vec3 up() { return Vec3(0, 1, 0); }
    static Vec3 right() { return Vec3(1, 0, 0); }
    static Vec3 forward() { return Vec3(0, 0, 1); }
};

inline Vec3 operator*(double scalar, const Vec3& v) { return v * scalar; }

} // namespace math
