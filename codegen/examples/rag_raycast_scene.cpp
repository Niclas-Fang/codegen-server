#include "demo_project/include/scene.h"
#include "demo_project/include/mesh.h"
#include "demo_project/include/camera.h"
#include <limits>
#include <functional>

using namespace math;
using namespace render;

// 实现鼠标点击选择场景中物体的射线检测逻辑
SceneNode* pickObject(Scene* scene, double mouseX, double mouseY, const Camera& camera) {
    Vec3 rayOrigin = camera.position;
    Vec3 rayDir = camera.screenToWorldRay(mouseX, mouseY);

    SceneNode* closest = nullptr;
    double closestDistance = std::numeric_limits<double>::max();

    std::function<void(SceneNode*)> checkNode = [&](SceneNode* node) {
        if (node->mesh && node->visible) {
            Vec3 min, max;
            node->mesh->computeBoundingBox();
            min = node->mesh->bounds.min;
            max = node->mesh->bounds.max;

            // AABB 射线检测算法
            double tmin = 0.0, tmax = std::numeric_limits<double>::max();
            for (int i = 0; i < 3; ++i) {
                double invD = 1.0 / (rayDir[i] + 1e-10);
                double t1 = (min[i] - rayOrigin[i]) * invD;
                double t2 = (max[i] - rayOrigin[i]) * invD;

                tmin = std::max(tmin, std::min(t1, t2));
                tmax = std::min(tmax, std::max(t1, t2));
            }

            if (tmin <= tmax && tmin < closestDistance) {
                closest = node;
                closestDistance = tmin;
            }
        }

        <cursor>
    };

    checkNode(scene->root.get());
    return closest;
}
