#include <iostream>
#include <optional>
#include <variant>
#include <string>
#include <map>

// 使用 std::variant 实现类型安全的配置解析器
using ConfigValue = std::variant<int, double, bool, std::string>;

class ConfigLoader {
public:
    // 设置配置项
    void set(const std::string& key, ConfigValue value) {
        config_[key] = std::move(value);
    }

    // 获取配置项（类型安全）
    template<typename T>
    std::optional<T> get(const std::string& key) const {
        auto it = config_.find(key);
        if (it == config_.end()) return std::nullopt;

        // 尝试提取指定类型的值
        const T* val = std::get_if<T>(&it->second);
        if (!val) return std::nullopt;
        return *val;
    }

    // 获取配置项，带默认值
    template<typename T>
    T getOr(const std::string& key, T defaultValue) const {
        auto val = get<T>(key);
        return val.value_or(defaultValue);
    }

    <cursor>

private:
    std::map<std::string, ConfigValue> config_;
    std::vector<std::string> loadOrder_;
};
