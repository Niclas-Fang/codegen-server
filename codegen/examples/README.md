# Graph-RAG Code Completion Examples

完整的 FIM (Fill-in-Middle) 和 RAG (Graph-RAG) 补全测试示例，每个文件包含 `<cursor>` 标记表示补全插入点。

## 目录结构

```
examples/
├── README.md                        # 本文件
├── run_all.sh                       # 一键运行脚本
├── demo_project/                    # RAG 知识库项目（需先索引）
│   ├── include/
│   │   ├── vec3.h                   # 3D 向量类
│   │   ├── matrix4.h                # 4x4 变换矩阵
│   │   ├── mesh.h                   # 网格/顶点/包围盒
│   │   ├── shader.h                 # 着色器编译/链接
│   │   ├── material.h               # PBR 材质系统
│   │   ├── camera.h                 # 相机/投影
│   │   ├── scene.h                  # 场景图/渲染命令
│   │   └── renderer.h              # 渲染器管线
│   └── src/
│       ├── vec3.cpp
│       ├── matrix4.cpp
│       └── mesh.cpp
├── fim_quick_sort.cpp               # FIM: 模板快速排序分区
├── fim_smart_pointer.cpp            # FIM: 自定义 UniquePtr
├── fim_event_bus.cpp                # FIM: 事件发布/订阅
├── fim_thread_pool.cpp              # FIM: 线程池工作循环
├── fim_config_loader.cpp            # FIM: 类型安全配置解析器
├── rag_setup_renderer.cpp           # RAG: 渲染管线初始化
├── rag_raycast_scene.cpp            # RAG: 射线-AABB 相交检测
├── rag_pbr_shader.cpp               # RAG: PBR 着色器创建
├── rag_frustum_cull.cpp             # RAG: 视锥体剔除
├── rag_mesh_loader.cpp              # RAG: 程序化球体生成
├── rag_transform_hierarchy.cpp      # RAG: 场景图变换更新
└── rag_scene_traversal.cpp          # RAG: 深度排序命令收集
```

## FIM vs RAG 对比

| 特性 | FIM (Fill-in-Middle) | RAG (Graph-RAG) |
|------|---------------------|-----------------|
| 端点 | `POST /api/v1/completion` | `POST /api/v1/chat` |
| 模型 | DeepSeek FIM | DeepSeek / OpenAI / Anthropic / Zhipu |
| 上下文 | 仅当前文件的前后文 | 项目知识图谱 + 向量检索 |
| 优势 | 局部语法、控制流、模式补全 | 跨文件 API 引用、类型推断、继承链 |
| 速度 | 快 (~10s) | 慢 (~30s) |
| 适用场景 | Lambda、循环、条件分支 | 调用项目中定义的类/方法 |

## 快速开始

### 1. 启动 Django 服务

```bash
cd ..
python3 manage.py runserver 8000
```

### 2. 索引 demo_project（RAG 必需）

```bash
./run_all.sh index
```

或手动运行：

```bash
cd ..
python3 -m completion.rag.indexer index examples/demo_project --project-path demo_project
```

### 3. 运行示例

```bash
# 运行所有示例（FIM + RAG）
./run_all.sh all

# 运行单个 FIM 示例
./run_all.sh fim fim_quick_sort.cpp

# 运行单个 RAG 示例
./run_all.sh rag rag_setup_renderer.cpp

# 对比 FIM vs RAG（同一个文件两种模式的差异）
./run_all.sh compare rag_setup_renderer.cpp

# 列出所有示例
./run_all.sh list
```

## 手动 curl 命令

### FIM 补全示例

**语法**: 提取 `<cursor>` 前的内容作为 `prompt`，后的内容作为 `suffix`

```bash
# === FIM 1: 快速排序分区逻辑 ===
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "auto partition = [&](Iterator low, Iterator high) -> Iterator {\n    auto pivot = *std::prev(high);\n    auto i = low;\n    for (auto j = low; j != std::prev(high); ++j) {\n        if (cmp(*j, pivot)) {",
    "suffix": "        }\n    }\n    std::iter_swap(i, std::prev(high));\n    return i;\n};",
    "max_tokens": 150
  }'
```

```bash
# === FIM 2: UniquePtr 移动赋值 ===
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "UniquePtr& operator=(UniquePtr&& other) noexcept {\n    if (this != &other) {\n        delete ptr_;\n        ptr_ = other.ptr_;\n        other.ptr_ = nullptr;\n    }",
    "suffix": "}\n\nT* get() const noexcept { return ptr_; }",
    "max_tokens": 100
  }'
```

```bash
# === FIM 3: 事件总线去重逻辑 ===
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "auto it = std::find_if(subscribers.begin(), subscribers.end(),\n    [&callback](const auto& pair) { return pair.first == callback; });",
    "suffix": "    subscribers.push_back({id, std::move(callback)});\n    return id;",
    "max_tokens": 100
  }'
```

```bash
# === FIM 4: 线程池析构函数 ===
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "for (auto& worker : workers_) {",
    "suffix": "    }",
    "max_tokens": 100
  }'
```

```bash
# === FIM 5: 配置解析器 API ===
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "~ConfigLoader() = default;\n\n// 从文件加载配置（JSON/TOML/YAML）\nbool loadFromFile(const std::string& filepath) {\n    std::ifstream file(filepath);\n    if (!file.is_open()) return false;\n\n    json data = json::parse(file);\n    for (auto& [key, value] : data.items()) {\n        if (value.is_number_integer()) {\n            set(key, value.get<int>());\n        } else if (value.is_number_float()) {\n            set(key, value.get<double>());\n        } else if (value.is_boolean()) {\n            set(key, value.get<bool>());\n        } else if (value.is_string()) {\n            set(key, value.get<std::string>());\n        }\n        loadOrder_.push_back(key);\n    }\n    return true;\n}\n\n// 保存配置到文件\nbool saveToFile(const std::string& filepath) const;\n\n// 列出所有配置键\nstd::vector<std::string> keys() const;\n\n// 移除配置项\nvoid remove(const std::string& key);\n\n// 合并其他配置\nvoid merge(const ConfigLoader& other);\n\n// 清空所有配置\nvoid clear() {\n    config_.clear();\n    loadOrder_.clear();\n}",
    "suffix": "",
    "max_tokens": 300
  }'
```

### RAG 补全示例

**语法**: context 中包含 prompt/suffix，project_path 指向已索引的项目

```bash
# === RAG 1: 渲染管线初始化 (+ Graph-RAG) ===
# 需要了解 Scene/Mesh/Material/Camera/Renderer 的 API
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "using namespace render;\n\nvoid renderFrame() {\n    Renderer renderer(1920, 1080);\n    renderer.enableShadows = true;\n    renderer.enableMSAA = true;\n    renderer.msaaSamples = 4;\n\n    if (!renderer.initialize()) {\n        std::cerr << \"Failed to initialize renderer\" << std::endl;\n        return;\n    }\n\n    Scene scene;\n\n    auto* ground = scene.createNode(\"Ground\");\n    ground->mesh = Mesh::createCube(10.0);\n    ground->material = Material::createPBR(math::Vec3(0.3, 0.5, 0.2), 0.0, 0.9);\n    ground->setPosition(math::Vec3(0, -0.5, 0));\n    ground->setScale(math::Vec3(10, 0.1, 10));\n\n    auto* cube = scene.createNode(\"Cube\");\n    cube->mesh = Mesh::createCube(1.0);\n    cube->material = Material::createDefault();\n    cube->setPosition(math::Vec3(0, 0.5, 0));\n\n    scene.camera.position = math::Vec3(5, 5, 5);\n    scene.camera.lookAt(math::Vec3(0, 0, 0));\n\n    renderer.beginFrame();\n    renderer.clear(math::Vec3(0.1, 0.1, 0.15));",
      "suffix": "    renderer.endFrame();\n}",
      "includes": []
    },
    "model": "deepseek-chat",
    "max_tokens": 300,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 2: 场景图递归遍历 (+ Graph-RAG) ===
# 需要了解 SceneNode.children 结构
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "std::function<void(SceneNode*)> checkNode = [&](SceneNode* node) {\n    if (node->mesh && node->visible) {\n        Vec3 min = node->mesh->bounds.min;\n        Vec3 max = node->mesh->bounds.max;\n\n        double tmin = 0.0, tmax = std::numeric_limits<double>::max();\n        for (int i = 0; i < 3; ++i) {\n            double invD = 1.0 / (rayDir[i] + 1e-10);\n            double t1 = (min[i] - rayOrigin[i]) * invD;\n            double t2 = (max[i] - rayOrigin[i]) * invD;\n            tmin = std::max(tmin, std::min(t1, t2));\n            tmax = std::min(tmax, std::max(t1, t2));\n        }\n        if (tmin <= tmax && tmin < closestDistance) {\n            closest = node;\n            closestDistance = tmin;\n        }\n    }",
      "suffix": "};",
      "includes": []
    },
    "model": "deepseek-chat",
    "max_tokens": 200,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 3: PBR 着色器 uniform 设置 (+ Graph-RAG) ===
# 需要 ShaderProgram.setUniform 重载方法签名
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "ShaderProgram* program = new ShaderProgram();\nprogram->attachShader(vertexShader);\nprogram->attachShader(fragmentShader);\n\nif (!program->link()) {\n    std::cerr << \"Shader program linking failed\" << std::endl;\n    delete program;\n    return nullptr;\n}\n\n// 设置标准 PBR uniform",
      "suffix": "return program;\n}",
      "includes": []
    },
    "model": "deepseek-chat",
    "max_tokens": 300,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 4: 视锥体剔除 (+ Graph-RAG) ===
# 需要 Vec3/Mesh/Camera/Renderer API
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "for (const auto& plane : frustumPlanes) {\n    Vec3 positiveVertex;",
      "suffix": "    double d = plane.normal.dot(positiveVertex) + plane.distance;\n    if (d < 0) return;\n}",
      "includes": ["#include \"demo_project/include/vec3.h\"", "#include \"demo_project/include/mesh.h\""]
    },
    "model": "deepseek-chat",
    "max_tokens": 200,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 5: 球体三角形索引生成 (+ Graph-RAG) ===
# 需要 Mesh.addTriangle 方法签名
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "for (int i = 0; i < segments; ++i) {\n    for (int j = 0; j < segments; ++j) {\n        int a = i * (segments + 1) + j;\n        int b = a + segments + 1;",
      "suffix": "    }\n}\n\nmesh->computeNormals();\nmesh->computeTangents();\nmesh->computeBoundingBox();",
      "includes": ["#include \"demo_project/include/mesh.h\""]
    },
    "model": "deepseek-chat",
    "max_tokens": 200,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 6: 场景图递归变换更新 (+ Graph-RAG) ===
# 需要 SceneNode.children 结构和 transform API
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "void updateWorldTransforms(SceneNode* node) {\n    if (!node) return;\n\n    Matrix4 worldMatrix;\n    if (node->parent) {\n        worldMatrix = node->parent->getWorldTransform() * node->transform;\n    } else {\n        worldMatrix = node->transform;\n    }\n\n    node->setTransform(worldMatrix);",
      "suffix": "}",
      "includes": ["#include \"demo_project/include/scene.h\"", "#include \"demo_project/include/matrix4.h\""]
    },
    "model": "deepseek-chat",
    "max_tokens": 200,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

```bash
# === RAG 7: 深度排序键计算 (+ Graph-RAG) ===
# 需要 Matrix4.transformPoint 和 Vec3 操作
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "Vec3 worldPos = cmd.transform.transformPoint(Vec3::zero());",
      "suffix": "commands.push_back(cmd);\n}\n\nfor (const auto& child : node->children) {\n    collectSortedCommands(child.get(), commands, cameraPos, layerMask);\n}",
      "includes": ["#include \"demo_project/include/scene.h\"", "#include \"demo_project/include/matrix4.h\""]
    },
    "model": "deepseek-chat",
    "max_tokens": 200,
    "provider": "deepseek",
    "use_rag": true,
    "use_graph_rag": true,
    "project_path": "demo_project"
  }'
```

## 技术说明

### `<cursor>` 标记

示例文件中的 `<cursor>` 标记表示代码补全的插入点：
- **标记前**的内容 → `prompt` 字段
- **标记后**的内容 → `suffix` 字段

`run_all.sh` 会自动提取这些内容并构造正确的 API 请求。

### FIM 补全原理

```
[prompt (before cursor)] █ [suffix (after cursor)]
                          ↑
                     模型在此处填充
```

FIM 模型看到前缀和后缀，预测中间的代码。适合局部模式补全。

### RAG (Graph-RAG) 补全原理

1. **检索阶段**: 查询知识图谱和向量索引，找到与当前上下文相关的代码实体和关系
2. **图遍历**: 沿着调用链、继承链扩展上下文
3. **增强阶段**: 将检索到的代码片段注入 prompt
4. **生成阶段**: LLM 基于增强后的 context 生成补全

适合需要跨文件类型信息、API 使用上下文等场景。

### 为什么需要 demo_project

RAG 需要已索引的代码库才能工作。demo_project 是一个迷你 3D 渲染引擎，包含：
- 8 个头文件定义核心 API
- 3 个源文件提供实现细节
- 类型之间存在丰富的调用、包含、继承关系

索引后，RAG 示例可以自动获取 Vec3、Mesh、Material、Camera 等类型的 API 信息。
