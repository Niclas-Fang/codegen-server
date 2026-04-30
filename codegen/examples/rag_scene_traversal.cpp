#include "demo_project/include/scene.h"
#include "demo_project/include/mesh.h"
#include "demo_project/include/material.h"
#include "demo_project/include/matrix4.h"

using namespace math;
using namespace render;

// 收集场景中所有可见节点的渲染命令，并按深度排序
void collectSortedCommands(SceneNode* node, std::vector<RenderCommand>& commands,
                           const Vec3& cameraPos, int layerMask) {
    if (!node || !node->visible) return;

    // 检查图层掩码
    if ((node->layerMask & layerMask) == 0) return;

    if (node->mesh && node->material) {
        RenderCommand cmd;
        cmd.mesh = node->mesh;
        cmd.material = node->material;
        cmd.transform = node->getWorldTransform();

        // 根据材质属性确定渲染阶段
        if (node->material->transparent) {
            cmd.pass = RenderPass::Transparent;
        } else if (node->material->emission > 0.0) {
            cmd.pass = RenderPass::Opaque;
        } else {
            cmd.pass = RenderPass::Opaque;
        }

        // 计算排序键（到相机的距离）
        Vec3 worldPos = cmd.transform.transformPoint(Vec3::zero());
        <cursor>

        commands.push_back(cmd);
    }

    for (const auto& child : node->children) {
        collectSortedCommands(child.get(), commands, cameraPos, layerMask);
    }
}
