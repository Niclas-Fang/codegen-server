#include "mesh.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <numeric>

namespace render {

void Mesh::addVertex(const Vertex& v) {
    vertices.push_back(v);
}

void Mesh::addTriangle(unsigned int a, unsigned int b, unsigned int c, unsigned int matIdx) {
    triangles.push_back({{a, b, c}, matIdx});
}

void Mesh::computeNormals() {
    for (auto& v : vertices) {
        v.normal = math::Vec3::zero();
    }

    for (const auto& tri : triangles) {
        Vertex& v0 = vertices[tri.indices[0]];
        Vertex& v1 = vertices[tri.indices[1]];
        Vertex& v2 = vertices[tri.indices[2]];

        math::Vec3 e1 = v1.position - v0.position;
        math::Vec3 e2 = v2.position - v0.position;
        math::Vec3 faceNormal = e1.cross(e2).normalized();

        v0.normal = v0.normal + faceNormal;
        v1.normal = v1.normal + faceNormal;
        v2.normal = v2.normal + faceNormal;
    }

    for (auto& v : vertices) {
        v.normal = v.normal.normalized();
    }
    normalsComputed = true;
}

void Mesh::computeBoundingBox() {
    bounds = {};
    for (const auto& v : vertices) {
        bounds.expand(v.position);
    }
}

Mesh* Mesh::createCube(double size) {
    Mesh* mesh = new Mesh("Cube");
    double h = size * 0.5;
    math::Vec3 positions[] = {
        {-h, -h, -h}, { h, -h, -h}, { h,  h, -h}, {-h,  h, -h},
        {-h, -h,  h}, { h, -h,  h}, { h,  h,  h}, {-h,  h,  h},
    };
    for (int i = 0; i < 8; ++i) {
        mesh->addVertex(Vertex(positions[i], positions[i].normalized()));
    }
    unsigned int indices[] = {
        0,1,2, 0,2,3,  4,5,6, 4,6,7,
        0,4,5, 0,5,1,  2,6,7, 2,7,3,
        0,3,7, 0,7,4,  1,5,6, 1,6,2,
    };
    for (size_t i = 0; i < 36; i += 3) {
        mesh->addTriangle(indices[i], indices[i+1], indices[i+2]);
    }
    mesh->computeNormals();
    mesh->computeBoundingBox();
    return mesh;
}

Mesh* Mesh::createSphere(double radius, int segments) {
    Mesh* mesh = new Mesh("Sphere");
    for (int i = 0; i <= segments; ++i) {
        double theta = M_PI * i / segments;
        for (int j = 0; j <= segments; ++j) {
            double phi = 2 * M_PI * j / segments;
            math::Vec3 pos(radius * std::sin(theta) * std::cos(phi),
                           radius * std::cos(theta),
                           radius * std::sin(theta) * std::sin(phi));
            mesh->addVertex(Vertex(pos, pos.normalized()));
        }
    }
    for (int i = 0; i < segments; ++i) {
        for (int j = 0; j < segments; ++j) {
            int a = i * (segments + 1) + j;
            int b = a + segments + 1;
            mesh->addTriangle(a, b, a + 1);
            mesh->addTriangle(b, b + 1, a + 1);
        }
    }
    mesh->computeBoundingBox();
    return mesh;
}

void Mesh::clear() {
    vertices.clear();
    triangles.clear();
    normalsComputed = false;
}

} // namespace render
