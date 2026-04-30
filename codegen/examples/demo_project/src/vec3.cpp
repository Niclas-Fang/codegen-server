#include "vec3.h"

namespace math {

Vec3 Vec3::cross(const Vec3& other) const {
    return Vec3(
        y * other.z - z * other.y,
        z * other.x - x * other.z,
        x * other.y - y * other.x
    );
}

Vec3 Vec3::normalized() const {
    double len = length();
    if (len < 1e-10) return Vec3(0, 0, 0);
    return Vec3(x / len, y / len, z / len);
}

} // namespace math
