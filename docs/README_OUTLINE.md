# SciHorizon-eLab README — Outline

> 大纲草案。给读者两种打开方式：
> - 一类读读 **SciVLABench**（评测/训练）
> - 一类读读 **SciHorizon-eLab** 编译器本身
> - 一类读读 **承诺过什么 + 怎么复现**
>
> 8 个主要章节，按"是什么 → 怎么做到 → 仓库里有什么 → 怎么装 → 怎么用 → 引用"。

---

## 1. Hero

**定位：** 项目一句话定义 + 主图 + 关键链接

- 标题 + 一句话定位（协议 → 任务编译）
- 公式块：τ = (E, P, S)（保留现状）
- Figure 1（[docs/images/figure1_framework.png](docs/images/figure1_framework.png)） + caption
- 三链接 badge：Paper PDF · GitHub · Hugging Face（README 现只有 paper+code，缺 HF 链接，可加可不加）

---

## 2. SciVLABench at a glance

**定位：** 让读者 3 秒知道"库规模多大、有什么、跟谁比"

- 数字表（51 / 30 / 300 / 15，**核一遍现状是否要补**）
- 五族名称 bullet（Liquid Handling / Mixing / Solid Handling / Thermal / Apparatus）
- 三行总结：每个任务包含什么；怎么生成轨迹；怎么评分
- 三种评测协议一句话各一条（Same-task / Held-out binding / Human-agent coordination）+ 指标列表 SR/SSR/PVR/latency
- **Table 1 对比图**（[docs/images/table1_comparison.png](docs/images/table1_comparison.png)）+ caption：与现有 benchmark 系统的位置
- **亮点数据一句**：ACT 49.7% / π₀.₅ 61.4% / 81% 认证率（**用最新口径核实**）

---

## 3. How the compiler works

**定位：** 三阶段机理解释 + repo 内模块位置

- 三阶段文字描述（Semantic-preserving environment compilation / Executable task specification / Simulation certification）—— 保留现 README 19–25 行内容
- repo 内模块链路 ASCII 图（保留现 29–33 行）
- 强调关键设计点（P 与 S 独立生成、视觉-语义双重校验、agentic feedback loop）

---

## 4. Code & documentation map

**定位：** 审稿人/复现同行的入口索引，**新增**，承接清单 #5、#13

子节：

- **4.1 Pipeline nodes & prompts** — 链接到 [docs/Node/](docs/Node/) 下 9 份节点文档；说明每个节点的 system prompt 内嵌在节点 .py 文件中（如 `analyzer.py` line 206 等），独立路径索引
- **4.2 Node design documents** — 节点输入/输出格式定义的位置
- **4.3 Inference settings & model configuration** — 指向 [scihorizon_elab/pipeline/config.py](scihorizon_elab/pipeline/config.py)（**重写后**的环境变量 + 默认模型）
- **4.4 Stage-wise SOP** — 安装、create_task、轨迹、训练、评测五条命令流

---

## 5. Repository contents

**定位：** 给"仓库里具体有什么"一个完整答复，**新增**，承接清单 #4、#6、#7、#12

子节：

- **5.1 Task inventory & operation-family breakdown** — 5 族任务清单 + 总计（**待 #4 实施时填实际计数**），把 Solid Handling 族归位（清单 #A）
- **5.2 Mixed-task & held-out configuration** ��� 混合训练三组配置 + 4 个 held-out 绑定场景位置（**承接 #7 补 lift_petri_dish**）
- **5.3 Human-agent coordination tasks** — 15 个 HIL 任务的位置与命名约定
- **5.4 Certification metadata** — 每个 certified task 自带的元数据字段、审计/认证记录位置（**承接 #12**）
- **5.5 Source scenarios & provenance** — 51 场景到文献的映射入口（**承接 #11**）
- **5.6 Concurrent-operation extension** — 30 个再生成任务 + HeatWithFlameCondition 入口（**承接 #10**）

---

## 6. Installation

**定位：** 让动手的人最快跑起来

- 保留 Option A（conda 环境 vlabench_2）+ Option B（pip + lock file）
- **修复路径错误**：删掉"Configuration lives in `scihorizon_elab/configs/`"——配置实际在 `scihorizon_elab/pipeline/config.py` 和 `scihorizon_elab/benchmark/configs/`（清单 #13）
- **submodule 段核实**：`third_party/openpi/` 是否真为 submodule，决定语句表述（清单 F）
- 子模块安装指引保留

---

## 7. Configuration

**定位：** 通用 API 配置（承接 #1 重写后的 config.py）

- 三个核心环境变量：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_NAME`、`LLM_VISION_MODEL_NAME`
- `.env.example` 位置与模板示例
- 默认值说明（千问 qwen-plus / qwen-vl-max）
- 如何切换到任何 OpenAI 兼容 API（vLLM / Ollama / OpenRouter / 自部署等）

---

## 8. Compile a protocol into a task

**定位：** 让"想自己编译"的人直接跑起来

- 4 个 `python -m scihorizon_elab.pipeline.create_task` 示例（保留现状 111–121 行）
- `--save-dir` / `--no-simulate` 说明
- 预期输出位置

---

## 9. Expert demonstrations & data conversion

**定位：** 拿到任务后如何生成轨迹

- `scripts/trajectory_generation.py` + 多进程 sh
- HDF5 → RLDS（Octo/OpenVLA）/ LeRobot (π₀.₅) / LeRobot 256×256 (ACT)
- `HF_HOME/lerobot/...` 默认路径

---

## 10. Training and evaluation

**定位：** 复现论文实验的命令流

- 三种 policy 超参表（保留现状 162–164）
- SOP 链接（`docs/SOP/`）
- `scripts/evaluate_policy.py` CLI 示例
- `sh/evaluation/example_multi_gpu_eval.sh` 多卡示例

---

## 11. Citation

**定位：** 引用入口

- 填好 bibtex（清单 #14，目前是空块）
- 论文附录指向：`docs/145_SciHorizon_eLab_An_Agentic (1)(2).pdf`

---

## 清单对接

| README 节 | 对接清单条目 |
|---|---|
| 2 SciVLABench | #A 五族归属 |
| 4.1 Prompts | #5 |
| 4.3 Inference | #5 |
| 5.1 Task inventory | #4 |
| 5.2 Mixed/held-out | #7 |
| 5.4 Certification | #12 |
| 5.5 Provenance | #11 |
| 5.6 Concurrent | #10 |
| 6 Installation | #13（路径错） |
| 7 Configuration | #1 config 重写 |
| 11 Citation | #14 |
