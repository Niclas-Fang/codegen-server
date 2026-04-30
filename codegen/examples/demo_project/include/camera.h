#pragma once
#include "vec3.h"
#include "matrix4.h"

namespace render {

class Camera {
public:
    math::Vec3 position;
    math::Vec3 target;
    math::Vec3 up;

    double fov;
    double aspectRatio;
    double nearPlane;
    double farPlane;

    double yaw;
    double pitch;
    double roll;

    Camera();

    math::Matrix4 getViewMatrix() const;
    math::Matrix4 getProjectionMatrix() const;
    math::Matrix4 getViewProjectionMatrix() const;

    void lookAt(const math::Vec3& target);
    void orbit(double deltaYaw, double deltaPitch);
    void zoom(double delta);
    void pan(double deltaX, double deltaY);
    void dolly(double delta);

    math::Vec3 getForward() const;
    math::Vec3 getRight() const;
    math::Vec3 getUp() const;

    void updateVectors();

    math::Vec3 screenToWorldRay(double screenX, double screenY) const;
    math::Vec3 worldToScreen(const math::Vec3& worldPos) const;

    void setPerspective(double fov, double aspect, double nearPlane, double farPlane);
    void setOrthographic(double left, double right, double bottom, double top,
                         double nearPlane, double farPlane);

    bool isPointVisible(const math::Vec3& point) const;
    bool isSphereVisible(const math::Vec3& center, double radius) const;

private:
    bool orthographic;
    double orthoLeft, orthoRight, orthoBottom, orthoTop;
};

} // namespace render
