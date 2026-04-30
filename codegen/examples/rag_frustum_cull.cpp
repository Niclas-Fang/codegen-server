#include "demo_project/include/scene.h"
#include "demo_project/include/camera.h"
#include "demo_project/include/renderer.h"
#include <array>
#include <functional>

using namespace math;
using namespace render;

// 视锥体剔除：只渲染在相机视野内的物体
void renderVisibleObjects(Scene* scene, Camera* camera, Renderer* renderer) {
    Matrix4 vp = camera->getViewProjectionMatrix();

    // 从 VP 矩阵提取六个视锥体平面
    struct Plane { Vec3 normal; double distance; };
    std::array<Plane, 6> frustumPlanes;

    // 提取平面
    auto extractPlane = [&](int row, double sign) {
        Plane p;
        p.normal.x = vp.m[3][0] + sign * vp.m[row][0];
        p.normal.y = vp.m[3][1] + sign * vp.m[row][1];
        p.normal.z = vp.m[3][2] + sign * vp.m[row][2];
        p.distance = vp.m[3][3] + sign * vp.m[row][3];
        return p;
    };

    frustumPlanes[0] = extractPlane(0, 1.0);   // 左平面
    frustumPlanes[1] = extractPlane(0, -1.0);  // 右平面
    frustumPlanes[2] = extractPlane(1, 1.0);   // 底部
    frustumPlanes[3] = extractPlane(1, -1.0);  // 顶部
    frustumPlanes[4] = extractPlane(2, 1.0);   // 近平面
    frustumPlanes[5] = extractPlane(2, -1.0);  // 远平面

    renderer->beginFrame();
    renderer->clear(Vec3(0.05, 0.05, 0.08));

    std::function<void(SceneNode*)> renderNode = [&](SceneNode* node) {
        if (!node->mesh || !node->material || !node->visible) return;

        Vec3 min, max;
        node->mesh->computeBoundingBox();
        min = node->mesh->bounds.min;
        max = node->mesh->bounds.max;

        // 视锥体-AABB 相交检测
        for (const auto& plane : frustumPlanes) {
            Vec3 positiveVertex;
            <cursor>

            double d = plane.normal.dot(positiveVertex) + plane.distance;
            if (d < 0) return; // 完全在平面外
        }

        RenderCommand cmd;
        cmd.mesh = node->mesh;
        cmd.material = node->material;
        cmd.transform = node->getWorldTransform();
        cmd.pass = RenderPass::Opaque;
        renderer->submit(cmd);
    };

    scene->root->traverse(renderNode);
    renderer->endFrame();
}
