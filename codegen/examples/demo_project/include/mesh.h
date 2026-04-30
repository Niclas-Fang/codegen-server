#pragma once
#include "vec3.h"
#include <vector>
#include <string>
#include <utility>

namespace render {

struct Vertex {
    math::Vec3 position;
    math::Vec3 normal;
    math::Vec3 tangent;
    math::Vec3 uv;

    Vertex() = default;
    Vertex(const math::Vec3& pos, const math::Vec3& norm)
        : position(pos), normal(norm), tangent(math::Vec3::zero()), uv(math::Vec3::zero()) {}
};

struct Triangle {
    unsigned int indices[3];
    unsigned int materialIndex;
};

struct BoundingBox {
    math::Vec3 min;
    math::Vec3 max;
    math::Vec3 center() const { return (min + max) * 0.5; }
    math::Vec3 extent() const { return max - min; }
    double diagonal() const { return (max - min).length(); }
    bool contains(const math::Vec3& point) const;
    bool intersects(const BoundingBox& other) const;
    void expand(const math::Vec3& point);
    void merge(const BoundingBox& other);
};

class Mesh {
public:
    std::vector<Vertex> vertices;
    std::vector<Triangle> triangles;
    std::string name;
    BoundingBox bounds;
    bool normalsComputed;

    Mesh() : normalsComputed(false) {}
    explicit Mesh(const std::string& name) : name(name), normalsComputed(false) {}

    void addVertex(const Vertex& v);
    void addTriangle(unsigned int a, unsigned int b, unsigned int c, unsigned int matIdx = 0);
    void computeNormals();
    void computeTangents();
    void computeBoundingBox();
    void validate();

    static Mesh* createCube(double size);
    static Mesh* createSphere(double radius, int segments);
    static Mesh* createPlane(double width, double depth);
    static Mesh* createCylinder(double radius, double height, int segments);
    static Mesh* loadFromOBJ(const std::string& path);
    static Mesh* loadFromGLTF(const std::string& path);

    size_t vertexCount() const { return vertices.size(); }
    size_t triangleCount() const { return triangles.size(); }
    bool isEmpty() const { return vertices.empty(); }
    void clear();

    void transform(const math::Matrix4& matrix);
};

} // namespace render
