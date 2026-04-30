#pragma once
#include "scene.h"
#include <vector>
#include <string>

namespace render {

class Renderer {
public:
    int width;
    int height;
    bool enableShadows;
    bool enableMSAA;
    bool enableHDR;
    int msaaSamples;

    Renderer(int width, int height);
    ~Renderer();

    bool initialize();
    void shutdown();

    void beginFrame();
    void submit(const RenderCommand& cmd);
    void renderScene(Scene* scene);
    void endFrame();

    void setViewport(int x, int y, int w, int h);
    void clear(const math::Vec3& color, bool clearDepth = true, bool clearStencil = false);

    void resize(int newWidth, int newHeight);

    unsigned int getFrameBuffer() const;
    unsigned int getDepthBuffer() const;
    unsigned int getColorTexture() const;

    void takeScreenshot(const std::string& path) const;

    void setSkybox(Mesh* skyboxMesh, ShaderProgram* skyboxShader);

    unsigned int createFrameBuffer(int w, int h);
    void attachColorBuffer(unsigned int fbo, unsigned int format);
    void attachDepthBuffer(unsigned int fbo);

private:
    void sortCommands();
    void executeShadowPass();
    void executeDepthPrepass();
    void executeOpaquePass();
    void executeSkyboxPass();
    void executeTransparentPass();
    void executePostProcess();

    std::vector<RenderCommand> commandQueue;
    Mesh* skyboxMesh;
    ShaderProgram* skyboxShader;
    unsigned int frameBuffer;
    unsigned int depthBuffer;
    unsigned int colorTexture;
};

class FrameStatistics {
public:
    double frameTime;
    int drawCalls;
    int triangleCount;
    int shadowCasters;

    FrameStatistics();

    void reset();
    std::string toString() const;
    void print() const;
};

} // namespace render
