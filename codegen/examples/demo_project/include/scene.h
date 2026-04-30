#pragma once
#include "mesh.h"
#include "material.h"
#include "camera.h"
#include "matrix4.h"
#include <vector>
#include <memory>
#include <functional>
#include <string>

namespace render {

enum class RenderPass {
    Shadow,
    DepthPrepass,
    Opaque,
    Skybox,
    Transparent,
    PostProcess,
    Overlay,
    Custom
};

struct RenderCommand {
    Mesh* mesh;
    Material* material;
    math::Matrix4 transform;
    RenderPass pass;
    float sortKey;
};

struct SceneNode {
    std::string name;
    math::Matrix4 transform;
    Mesh* mesh;
    Material* material;
    std::vector<std::unique_ptr<SceneNode>> children;
    SceneNode* parent;
    bool visible;
    bool castShadow;
    int layerMask;

    SceneNode(const std::string& name);

    void addChild(std::unique_ptr<SceneNode> child);
    void removeChild(const std::string& name);
    SceneNode* findChild(const std::string& name);
    std::vector<SceneNode*> findChildrenByTag(const std::string& tag);

    math::Matrix4 getWorldTransform() const;
    math::Matrix4 getInverseWorldTransform() const;

    void setPosition(const math::Vec3& pos);
    void setRotation(const math::Vec3& euler);
    void setScale(const math::Vec3& scale);
    void setTransform(const math::Matrix4& mat);

    math::Vec3 getWorldPosition() const;
    void lookAt(const math::Vec3& target, const math::Vec3& up = math::Vec3::up());

    void traverse(const std::function<void(SceneNode*)>& visitor);
    void traverseBreadthFirst(const std::function<void(SceneNode*)>& visitor);
};

class Scene {
public:
    std::unique_ptr<SceneNode> root;
    Camera camera;
    std::vector<math::Vec3> lights;

    Scene();

    SceneNode* createNode(const std::string& name, SceneNode* parent = nullptr);
    void destroyNode(const std::string& name);
    SceneNode* findNode(const std::string& name);

    void update(double deltaTime);
    void render();
    void collectRenderCommands(std::vector<RenderCommand>& commands);

    SceneNode* raycast(const math::Vec3& origin, const math::Vec3& direction) const;
    std::vector<SceneNode*> queryFrustum(const math::Matrix4& frustum) const;
    std::vector<SceneNode*> querySphere(const math::Vec3& center, double radius) const;

    void clear();
    size_t nodeCount() const;

    void serialize(const std::string& path);
    static Scene* deserialize(const std::string& path);
};

} // namespace render
