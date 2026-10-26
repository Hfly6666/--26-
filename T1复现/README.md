# T1 论文公开数据复现

论文：Qi et al. (2023), *A Practical End-to-End Inventory Management Model with Deep Learning*, Management Science 69(2), 759–773. DOI: 10.1287/mnsc.2022.4564.

## 查看报告

打开 `output/T1_论文复现报告.html`。图表、样式与2607个SKU的交互数据已嵌入，离线可用。

## 实际完成范围

- 作者公开3000行/2607个SKU的离线评价数值单元格重跑；全部7种方法用独立路径模拟交叉验证。
- 公开现场四组各500个单位的成本、t检验、回归、DiD、窗口与权重敏感性。
- 500个处理单位与55,333个候选的逻辑回归、协变量近邻匹配；另做真正的倾向得分近邻诊断。
- 1000个单周期及100个两周期小实例的事后最优标签枚举验证。
- 负订单、Normal公式、提前期窗口、常数项、旧笔记本输出和观察天数审计。

公开包未提供完整训练数据、132维完整输入、模型权重及原始训练程序，本项目没有重训原网络；不能称为完整复现论文所有实验。报告中论文全量数字与本次实际重算分别列出。

## 复运行

Python 3.12环境：

```powershell
python -m pip install -r requirements.txt
python bootstrap.py replicate.py
python bootstrap.py build_report.py
python bootstrap.py validate_delivery.py
node test_report.cjs
python bootstrap.py package_delivery.py
```

前三个Python数值脚本不联网，不需要GPU。`bootstrap.py` 优先寻找同级 `A1复现/vendor` 或本目录 `vendor`，否则使用当前环境。单独解压使用时安装requirements即可。Node用于交互脚本测试；数值复运行与查看HTML无需Node。可选的 `node browser_qa.cjs` 使用Node内置WebSocket和本地Chrome/Edge，精确检查1440像素与430像素视口、页面滚动和交互，并保存截图。

跨平台图表优先使用微软雅黑或文泉驿；若环境无中文字体，需安装可用中文字体并在 `build_report.py` 的字体候选列表配置路径。

## 文件结构

- `upstream/`：原包提取材料，保留CSV、DOCX及 `.ipynb_checkpoints/` 里的笔记本，未改写上游源文件。
- `sources/`：输入PDF/ZIP副本、文本提取与PDF关键页图像。
- `results/`：实际重算的CSV、JSON、原现场笔记本运行日志和校验结果。
- `output/figures/`：科学图表PNG；HTML内也已嵌入。
- `output/T1_论文复现报告.html`：正式HTML交付。

固定随机种子：20261025。数值版本、文件SHA-256、执行单元格编号见results中的环境和审计JSON。

## 关键解释

原代码口径下RNN平均总成本3036.76，低于其他非事后方法；只截断负订单后，GBM和BM2均低于RNN。现场后期累计成本下降55.46%，但处理/对照平均计费天数为20.096/27.124；按总观察天数归一化后降幅不同。原无常数项回归的库存天数系数不显著；加入论文式(11)的常数项后为显著负向。现场DiD的历史保存p值不等于本次顺序重跑p值。详细依据与限制均在HTML中。

借助AI完成论文阅读、代码整理与报告生成，数值由本地Python真实计算。原论文与数据权利归相应权利人；本包用于课程复现提交与核查。
