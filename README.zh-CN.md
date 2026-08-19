# Deep Paper Reader Skill

<div align="center">

[English](README.md) | **简体中文**

</div>

> 一个面向多学科单篇论文理解、精读与批判性审查的证据驱动型 Codex Skill。

Deep Paper Reader 可以将本地 PDF（Portable Document Format，便携式文档格式）、PDF 直链、arXiv 论文、DOI（Digital Object Identifier，数字对象唯一标识符）或可识别的论文标题，转化为结构清晰的 Markdown 阅读报告。它支持快速阅读、深度阅读与批判性审查，并让重要结论能够追溯到论文原文。

## 为什么开发这个项目

许多论文阅读工具能够概括内容，却容易混淆作者主张、论文证据和模型自己的推断。Deep Paper Reader 将三者的明确区分作为核心产品要求。

项目面向技术论文、实验论文、理论与数学论文、系统与数据集论文、综述、哲学、人文学科和社会科学论文，并根据论文类型采用不同的阅读与证据审查标准，而不是强行套用同一套评价模板。

## 工作流程

```text
输入论文
→ 检查来源与访问状态
→ 选择阅读模式
→ 判断论文类型
→ 提取正文与证据
→ 审查中心主张与证据
→ 生成结构化 Markdown 报告
→ 完成最终校验
```

## 阅读模式

- `quick_read`：快速理解研究问题、核心思想、主要结论、决定性证据和阅读价值。
- `deep_read`：系统梳理概念、结构、方法或论证、证据、贡献与局限。
- `critical_review`：检验中心主张是否得到充分支持，并识别最关键的证据缺口。

## 当前能力

项目目前包含：

- 完整的 Skill 阅读工作流；
- 包含论文定位和主张安全边界的报告模板；
- 针对不同论文类型的审查路线；
- 证据使用与不确定性处理规则；
- Codex 界面元数据；
- 对本地 PDF、PDF 网址、arXiv、DOI、出版商页面和论文标题的输入准备；
- 带 PDF 有效性检查和访问状态记录的论文获取流程；
- 具有稳定页码—文本块定位符的正文提取，以及光学字符识别提示；
- 章节结构重建和可追踪的候选主张提取；
- 从 arXiv 源文件优先提取图片、图注和章节上下文；
- 具有受控判断字段、证据位置检查和人工决策关卡的主张—证据记录；
- 可保留核心主张、补充遗漏主张并安全舍弃无关候选的紧凑审查覆盖文件；
- 从论文输入运行到主张审查准备阶段的跨平台 Python 流水线；
- 对报告结构、证据位置、图片、编码、重复内容和数学兼容性的最终校验；
- 自动化回归测试。

当前真实论文验证已经覆盖人文学科论证论文和长篇技术教程综述。最终学术判断仍由人工或智能体复核，不会仅凭关键词匹配自动决定。

## 运行方法

在项目根目录运行：

```bash
python3 scripts/run_pipeline.py \
  --paper "<论文输入>" \
  --output-root "<输出目录>" \
  --mode deep_read
```

统一流水线会准备论文来源、可追踪正文、阅读地图、图片和 `evidence/claims.json`，然后停在 `ready_for_claim_review`，等待对候选主张及其相邻原文进行复核。

完成主张审查后运行：

```bash
python3 scripts/claim_records.py apply-review \
  --workspace "<论文工作区>" \
  --review "<紧凑审查覆盖文件.json>"

python3 scripts/claim_records.py validate \
  --workspace "<论文工作区>"

python3 scripts/validate_report.py \
  --workspace "<论文工作区>" \
  --final
```

如果流程中断，可以使用下面的命令继续已有工作区，并保留已经完成的人工主张判断：

```bash
python3 scripts/run_pipeline.py --resume-workspace "<论文工作区>"
```

## 真实论文验证

第一次正向验证使用 Henrik Bohlin 2009 年的哲学论文 *Sympathy, Understanding, and Hermeneutics in Hume’s Treatise*。测试发现并修复了交替出现的期刊页眉、被误判为标题的编号脚注、范围过宽的候选主张以及人工审查操作繁琐等问题。修订后的流程识别出11个文档章节，生成40条排序后的候选主张，保留8条经过审查的中心主张，并在无警告的情况下通过证据校验和最终报告校验。

第二次正向验证通过 DOI 读取 Kevin P. Murphy 的253页 arXiv 教程 *Reinforcement Learning: An Overview*。测试验证了 DOI 到 arXiv 的来源解析、源文件图片提取和长文档综述处理，同时发现并修复了仅含页码的留白页被当成提取失败、伪代码和公式被误判为标题、局部章节描述压过综述级中心主张等问题。修订后的流程将6页识别为有意留白，重建227个章节，提取62幅图片，复核40条自动候选并补充8条论文级中心主张，最终无警告地通过两项校验。

出于版权与仓库体积考虑，测试论文原文和生成的阅读工作区不包含在本仓库中。

## 支持的论文输入

来源解析器支持：

- 本地 PDF 文件；
- PDF 直链；
- arXiv 链接或编号；
- DOI；
- 出版商论文页面；
- 可识别的论文标题。

只提供标题时，系统会进入权威来源检索，而不会自动认定某个模糊匹配结果。存在 arXiv 源文件包时，系统还会运行图片提取流程。

## 自动化测试

在项目根目录运行：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
```

当前自动化测试共42项。

## 项目结构

```text
.
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── LICENSE
├── requirements.txt
├── agents/
├── assets/
├── references/
└── scripts/
```

## 使用示例

```text
使用 $deep-paper-reader 深度阅读这篇论文，并生成一份证据可追溯的中文报告。
```

## 设计原则

- 先解释论文，再进行评价；
- 根据论文类型选择证据标准；
- 明确区分作者主张与报告推断；
- 公开访问范围和文本提取限制；
- 生成一份完整、可复用的 Markdown 报告；
- 只有在决定会实质改变结果时才请求人工确认。

## 许可证

MIT
