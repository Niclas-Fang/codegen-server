#include <vector>
#include <type_traits>
#include <concepts>
#include <algorithm>
#include <random>

// 实现通用快速排序，支持自定义比较器和投影
template<typename Iterator, typename Compare = std::less<>>
void quick_sort(Iterator begin, Iterator end, Compare cmp = Compare{}) {
    if (std::distance(begin, end) <= 1) return;

    auto partition = [&](Iterator low, Iterator high) -> Iterator {
        auto pivot = *std::prev(high);
        auto i = low;

        for (auto j = low; j != std::prev(high); ++j) {
            if (cmp(*j, pivot)) {
                <cursor>
            }
        }

        std::iter_swap(i, std::prev(high));
        return i;
    };

    auto pivot = partition(begin, end);
    quick_sort(begin, pivot, cmp);
    quick_sort(std::next(pivot), end, cmp);
}
