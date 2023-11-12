对应 `WaveFunctionCollapse` 实现的 `Python` 版本，原本的 `WaveFunctionCollapse` 有两种采样方式：

- `OverlappingModel` 已实现，这个算法本身比较暴力，时间复杂度达到了 `O(n^4)`，采样图尺寸的上升导致的直接结果就是非常恐怖的耗时提升
- `SimpleTiledModel` 待实现

实现后顺便和原来的 `C#` 版本实现进行了耗时对比，原来的 `C#` 实现执行速度完爆 `Python` 实现，不打算继续实现 `SimpleTiledModel` 了（虽然说可以优化，但我更宁愿沿用 `C#` 去优化），此仓库留作纪念 orz