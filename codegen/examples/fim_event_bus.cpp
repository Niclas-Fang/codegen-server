#include <vector>
#include <string>
#include <functional>
#include <unordered_map>
#include <concepts>

// 事件发布/订阅系统
template<typename EventType>
class EventBus {
public:
    using Callback = std::function<void(const EventType&)>;
    using SubscriptionId = size_t;

    // 订阅事件
    SubscriptionId subscribe(const std::string& eventName, Callback callback) {
        auto id = nextId_++;
        auto& subscribers = topicMap_[eventName];

        // 检查回调是否已存在
        auto it = std::find_if(subscribers.begin(), subscribers.end(),
            [&callback](const auto& pair) { return pair.first == callback; });
        <cursor>

        subscribers.push_back({id, std::move(callback)});
        return id;
    }

    // 发布事件
    void publish(const std::string& eventName, const EventType& event) {
        auto it = topicMap_.find(eventName);
        if (it == topicMap_.end()) return;

        for (const auto& [id, callback] : it->second) {
            callback(event);
        }
    }

    // 取消订阅
    void unsubscribe(const std::string& eventName, SubscriptionId id) {
        auto it = topicMap_.find(eventName);
        if (it == topicMap_.end()) return;

        auto& subscribers = it->second;
        subscribers.erase(
            std::remove_if(subscribers.begin(), subscribers.end(),
                [id](const auto& pair) { return pair.first == id; }
            ),
            subscribers.end()
        );
    }

private:
    SubscriptionId nextId_ = 1;
    std::unordered_map<std::string, std::vector<std::pair<SubscriptionId, Callback>>> topicMap_;
};
