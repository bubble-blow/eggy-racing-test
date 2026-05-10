# Eggy Racing (PyOpenGL)

两个入口：

- `python editor.py`：地图编辑器（按方格编辑高度）
- `python race.py`：单机竞速体验（球体 + 方向键）

## 编辑器说明

- 方向键：移动光标
- `Space`：将当前格子设置为刷子高度
- `Tab`：切换模式 `fixed` / `adaptive`
  - `fixed`：只改当前格子高度
  - `adaptive`：改当前格子并平滑周围邻居
- `+/-`：增减刷子高度
- `S`：保存地形
- `Esc`：退出并保存

## 竞速说明

- 方向键上/下：线性加速/减速
- 方向键左/右：视角转向（并改变前进方向）
- `Esc`：退出

## 地形与碰撞统一

地形绘制与碰撞/贴地高度采样共享同一份数据文件：`data/terrain.json`。
`terrain.py` 同时提供：

- 网格渲染 `draw_terrain`
- 高度采样 `sample_height`（用于球体碰撞贴地）

