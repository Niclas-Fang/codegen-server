#include <iostream>
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <functional>
#include <future>

// 简化的线程池实现
class ThreadPool {
public:
    explicit ThreadPool(size_t numThreads) : stop_(false) {
        for (size_t i = 0; i < numThreads; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(queueMutex_);
                        condition_.wait(lock, [this] {
                            return stop_ || !taskQueue_.empty();
                        });

                        if (stop_ && taskQueue_.empty()) return;

                        task = std::move(taskQueue_.front());
                        taskQueue_.pop();
                    }
                    task();
                }
            });
        }
    }

    ~ThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queueMutex_);
            stop_ = true;
        }
        condition_.notify_all();
        for (auto& worker : workers_) {
            <cursor>
        }
    }

    template<typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args)
        -> std::future<typename std::invoke_result_t<F, Args...>>
    {
        using ReturnType = typename std::invoke_result_t<F, Args...>;

        auto task = std::make_shared<std::packaged_task<ReturnType()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );

        auto result = task->get_future();

        {
            std::unique_lock<std::mutex> lock(queueMutex_);
            if (stop_) {
                throw std::runtime_error("ThreadPool已停止");
            }
            taskQueue_.emplace([task]() { (*task)(); });
        }
        condition_.notify_one();
        return result;
    }

    size_t workerCount() const { return workers_.size(); }
    size_t pendingTasks() const {
        std::unique_lock<std::mutex> lock(queueMutex_);
        return taskQueue_.size();
    }

private:
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> taskQueue_;
    mutable std::mutex queueMutex_;
    std::condition_variable condition_;
    bool stop_;
};
