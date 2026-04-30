#include "demo_project/include/mesh.h"
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <algorithm>

using namespace math;
using namespace render;

// 程序化生成球体网格（带切线计算）
Mesh* createProceduralSphere(double radius, int segments) {
    Mesh* mesh = new Mesh("ProceduralSphere");

    // 生成顶点数据
    for (int i = 0; i <= segments; ++i) {
        double theta = M_PI * i / segments;
        double sinTheta = std::sin(theta);
        double cosTheta = std::cos(theta);

        for (int j = 0; j <= segments; ++j) {
            double phi = 2.0 * M_PI * j / segments;
            double sinPhi = std::sin(phi);
            double cosPhi = std::cos(phi);

            Vertex v;
            v.position = Vec3(
                radius * sinTheta * cosPhi,
                radius * cosTheta,
                radius * sinTheta * sinPhi
            );
            v.normal = v.position.normalized();
            v.tangent = Vec3(-sinPhi, 0, cosPhi).normalized();
            v.uv = Vec3(
                static_cast<double>(j) / segments,
                static_cast<double>(i) / segments,
                0
            );

            mesh->addVertex(v);
        }
    }

    // 生成三角形索引
    for (int i = 0; i < segments; ++i) {
        for (int j = 0; j < segments; ++j) {
            int a = i * (segments + 1) + j;
            int b = a + segments + 1;

            <cursor>
        }
    }

    mesh->computeNormals();
    mesh->computeTangents();
    mesh->computeBoundingBox();
    mesh->validate();
    return mesh;
}
