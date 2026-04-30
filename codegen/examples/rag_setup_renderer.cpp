#include "demo_project/include/renderer.h"
#include "demo_project/include/scene.h"
#include "demo_project/include/mesh.h"
#include "demo_project/include/material.h"
#include "demo_project/include/camera.h"

using namespace render;

// 初始化渲染管线并渲染一帧
void renderFrame() {
    Renderer renderer(1920, 1080);
    renderer.enableShadows = true;
    renderer.enableMSAA = true;
    renderer.msaaSamples = 4;

    if (!renderer.initialize()) {
        std::cerr << "Failed to initialize renderer" << std::endl;
        return;
    }

    Scene scene;

    // 创建地面
    auto* ground = scene.createNode("Ground");
    ground->mesh = Mesh::createCube(10.0);
    ground->material = Material::createPBR(math::Vec3(0.3, 0.5, 0.2), 0.0, 0.9);
    ground->setPosition(math::Vec3(0, -0.5, 0));
    ground->setScale(math::Vec3(10, 0.1, 10));

    // 创建立方体
    auto* cube = scene.createNode("Cube");
    cube->mesh = Mesh::createCube(1.0);
    cube->material = Material::createDefault();
    cube->setPosition(math::Vec3(0, 0.5, 0));

    // 设置相机
    scene.camera.position = math::Vec3(5, 5, 5);
    scene.camera.lookAt(math::Vec3(0, 0, 0));

    renderer.beginFrame();
    renderer.clear(math::Vec3(0.1, 0.1, 0.15));

    <cursor>

    renderer.endFrame();
}
