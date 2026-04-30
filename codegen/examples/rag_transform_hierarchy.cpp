#include "demo_project/include/scene.h"
#include "demo_project/include/matrix4.h"
#include <functional>

using namespace math;
using namespace render;

// 递归更新场景图中所有节点的世界变换矩阵
void updateWorldTransforms(SceneNode* node) {
    if (!node) return;

    Matrix4 worldMatrix;
    if (node->parent) {
        worldMatrix = node->parent->getWorldTransform() * node->transform;
    } else {
        worldMatrix = node->transform;
    }

    // 将世界矩阵写回节点的 transform（更新缓存）
    node->setTransform(worldMatrix);

    <cursor>
}
