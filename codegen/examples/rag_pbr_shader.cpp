#include "demo_project/include/shader.h"
#include "demo_project/include/material.h"
#include <iostream>
#include <string>

using namespace render;

// 创建 PBR 渲染所需的着色器程序
ShaderProgram* createPBRShader() {
    Shader* vertexShader = Shader::fromFile(ShaderType::Vertex, "assets/shaders/pbr.vert");
    Shader* fragmentShader = Shader::fromFile(ShaderType::Fragment, "assets/shaders/pbr.frag");

    if (!vertexShader || !fragmentShader) {
        std::cerr << "Failed to load PBR shader files" << std::endl;
        delete vertexShader;
        delete fragmentShader;
        return nullptr;
    }

    if (!vertexShader->compile()) {
        std::cerr << "Vertex shader error: " << vertexShader->getCompileLog() << std::endl;
        delete vertexShader;
        delete fragmentShader;
        return nullptr;
    }

    if (!fragmentShader->compile()) {
        std::cerr << "Fragment shader error: " << fragmentShader->getCompileLog() << std::endl;
        delete vertexShader;
        delete fragmentShader;
        return nullptr;
    }

    ShaderProgram* program = new ShaderProgram();
    program->attachShader(vertexShader);
    program->attachShader(fragmentShader);

    if (!program->link()) {
        std::cerr << "Shader program linking failed" << std::endl;
        delete program;
        delete vertexShader;
        delete fragmentShader;
        return nullptr;
    }

    <cursor>

    return program;
}
