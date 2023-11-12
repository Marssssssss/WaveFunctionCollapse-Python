对应 `WaveFunctionCollapse` 实现的 `Python` 版本，原本的 `WaveFunctionCollapse` 有两种采样方式：

- `OverlappingModel` 已实现，这个算法本身比较暴力，时间复杂度达到了 `O(n^4)`，采样图尺寸的上升导致的直接结果就是非常恐怖的耗时提升

优化了下之前循环里面的 `deepcopy`，现在的运行速度要更快了，但还需要进一步优化。

TODO:

- 实现 `SimpleTiledModel`
- 接入原仓库的 `xml`，以及各个生成参数