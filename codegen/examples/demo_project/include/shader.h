#pragma once
#include "vec3.h"
#include <string>
#include <unordered_map>
#include <vector>

namespace render {

enum class ShaderType {
    Vertex,
    Fragment,
    Geometry,
    Compute,
    TessellationControl,
    TessellationEvaluation
};

class Shader {
public:
    ShaderType type;
    std::string source;
    std::string path;
    unsigned int handle;
    bool compiled;

    Shader(ShaderType type, const std::string& source);
    ~Shader();

    bool compile();
    std::string getCompileLog() const;
    bool isValid() const { return compiled && handle != 0; }

    static Shader* fromFile(ShaderType type, const std::string& path);
    static Shader* fromSource(ShaderType type, const std::string& source);

    static std::string shaderTypeToString(ShaderType type);
};

class ShaderProgram {
public:
    unsigned int handle;
    std::unordered_map<std::string, int> uniformLocations;
    std::vector<Shader*> attachedShaders;
    bool linked;

    ShaderProgram();
    ~ShaderProgram();

    bool attachShader(Shader* shader);
    bool link();
    void use();
    void unuse();

    bool isValid() const { return linked && handle != 0; }

    void setUniform(const std::string& name, float value);
    void setUniform(const std::string& name, const math::Vec3& value);
    void setUniform(const std::string& name, const math::Matrix4& value);
    void setUniform(const std::string& name, int value);
    void setUniform(const std::string& name, bool value);
    void setUniformArray(const std::string& name, const float* values, int count);
    void setUniformTexture(const std::string& name, int textureUnit);

    int getUniformLocation(const std::string& name);
    bool hasUniform(const std::string& name);

    static ShaderProgram* fromFiles(const std::vector<std::pair<ShaderType, std::string>>& shaders);
    static ShaderProgram* createCompute(const std::string& path);
};

} // namespace render
