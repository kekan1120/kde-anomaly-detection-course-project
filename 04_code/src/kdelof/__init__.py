"""KDE / LOF 异常检测课程项目 —— C（实现与复现）的正式实现。

模块划分（每一步对应协议里的一条要求，便于逐条追溯）：

===============  ==========================================================
``protocol``     读取并校验预注册配置（唯一数值事实来源）
``dgp``          按登记的独立种子生成 train / validation / test 与一维示例
``scoring``      两个检测器的打分 + 手写参考实现 + 得分方向断言
``calibration``  用 validation 正常分数校准阈值（inverted_cdf 0.99）
``metrics``      AUC / AP / 错排配对数 / 混淆矩阵 / 分簇误报率
``peaks``        一维密度曲线的峰结构（prominence 口径）
``experiment``   E0 / E1 / E2 / E3 与 P1 多种子
``reporting``    CSV / JSON / 运行日志 / 自检图
===============  ==========================================================
"""

__all__ = [
    "protocol",
    "dgp",
    "scoring",
    "calibration",
    "metrics",
    "peaks",
    "experiment",
    "reporting",
]
