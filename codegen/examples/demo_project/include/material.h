#pragma once
#include "vec3.h"
#include "shader.h"
#include <string>
#include <unordered_map>
#include <variant>

namespace render {

enum class MaterialPropertyType {
    Float,
    Vec3,
    Int,
    Bool,
    Texture2D,
    TextureCube,
    Mat4
};

struct MaterialProperty {
    std::string name;
    MaterialPropertyType type;
    std::variant<float, math::Vec3, int, bool, std::string, math::Matrix4> value;

    MaterialProperty() = default;
    MaterialProperty(const std::string& name, float v);
    MaterialProperty(const std::string& name, const math::Vec3& v);
    MaterialProperty(const std::string& name, int v);
    MaterialProperty(const std::string& name, bool v);
    MaterialProperty(const std::string& name, const std::string& texturePath);
};

class Material {
public:
    std::string name;
    math::Vec3 baseColor;
    float metallic;
    float roughness;
    float opacity;
    float emission;
    ShaderProgram* shader;
    std::unordered_map<std::string, MaterialProperty> properties;
    bool transparent;
    bool doubleSided;
    int renderQueue;

    Material();
    explicit Material(const std::string& name);

    void setProperty(const std::string& name, float value);
    void setProperty(const std::string& name, const math::Vec3& value);
    void setProperty(const std::string& name, int value);
    void setProperty(const std::string& name, bool value);
    void setProperty(const std::string& name, const std::string& texturePath);
    void setProperty(const std::string& name, const math::Matrix4& value);

    bool hasProperty(const std::string& name) const;
    const MaterialProperty* getProperty(const std::string& name) const;

    void bind();
    void unbind();

    static Material* createDefault();
    static Material* createPBR(const math::Vec3& color, float metallic, float roughness);
    static Material* createUnlit(const math::Vec3& color);
    static Material* createEmissive(const math::Vec3& color, float intensity);

    void cloneFrom(const Material* other);
};

} // namespace render
