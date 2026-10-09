# 最终代码仓库发布对齐清单

> 用途：把 rebuttal 承诺与 `SciHorizon-ELAB` 仓库现状的差距逐条记录；每行是**一个问题** + **双方已达成一致的解决方案**。
> 维护：`docs/release_alignment_checklist.md`
> 状态字段（约定）：⏳ 待讨论 · ✅ 已确定方案 · 🔧 修复中 · ✨ 已修复

| # | 问题 | 解决方案 | 状态 |
|---|---|---|---|
| 1 | API key 泄露：`pipeline/config.py` 硬编码 2 个 key 与第三方代理地址，且已存在于公开仓库 `target/master`；同时需清除全部 Anthropic/claude 字样，模型口径改为千问（Qwen） | ① 整体重写 `pipeline/config.py` 为**通用 API 配置**：环境变量 `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL_NAME`（+`LLM_VISION_MODEL_NAME`）控制，默认值取千问（文本 `qwen-plus`、视觉 `qwen-vl-max`，dashscope OpenAI 兼容端点），可接入任何 OpenAI 兼容 API，仓库内零密钥；提供 `create_llm(vision=False)` 统一工厂（基于 `langchain-openai` 的 `ChatOpenAI`）与 `.env.example` ② 5 个 pipeline 节点（analyzer/normalizer/skill_planner/condition_planner/reviewer）的 `langchain_anthropic` import 与 `ChatAnthropic` 实例化替换为 `AgentConfig.create_llm()` ③ reviewer 多模态消息格式从 Anthropic 专有格式改为 OpenAI 兼容 `image_url` 格式 ④ `requirements-lock.txt`/`environment.yml`：`langchain-anthropic` → `langchain-openai` ⑤ docs/Node/ 文档同步去除 Anthropic/claude 字样 ⑥ **方案 b**：发布分支移除 VLM 遗留评测模块——`benchmark/evaluation/model/vlm/`（整目录）、`evaluator/vlm.py`、`scripts/evaluate_vlm.py`、`scripts/create_vlm_task.py`、`sh/evaluate_vlms.sh`、`docs/render_vlm_dataset_guide.md`，并清理 `evaluation/__init__.py`、`evaluator/__init__.py` 的对应 import（`pipeline/nodes/vlm_data.py` 属 compiler 链路，保留） ⑦ 用户侧自行作废/轮换已泄露的 2 个 key（git 历史中已存在，只能由持有人操作） | ✨ 已修复（①–⑥ 完成，⑦ 待用户轮换 key） |
| 2 | 公开仓库落后本地（缺 workspace_interaction 族、HIL 任务、HeatWithFlameCondition 等；另 master 新增 6D 提交 cc2c6c3 未进 upload） | 在 upload 分支逐项修复后统一推送 target 仓库；实施前先 `git merge master` 把 cc2c6c3 并入 upload。每个问题的修复独立成提交 | ✅ 已确定方案 |
| 3 | 化学反应库仅 5 条，rebuttal 声称 "hundreds of encoded reactions"，规模严重不符 | 扩充 `solute_reaction.py` 的 `REACTIONS` 至 100 条 + 同步补全 `SOLUTE2RGBA` 产物颜色条目（无色沉淀 `[1,1,1,0.7]`、可溶无色 `[1,1,1,0.3]`、有色产物按真实颜色）。选反应范围：中学/大一常见复分解、中和、沉淀反应（氯化物/硝酸盐/硫酸盐/碳酸盐/氢氧化物两两组合，对照溶解性表系统生成）。实施方式：一次性脚本生成 + 人工抽查 20 条。⚠️ 论文措辞建议同步从 "hundreds" 改为 "100+" 以免对不上 | ✅ 已确定方案 |
| 4 | README 缺任务清单与五族分布（hmhw Q1 承诺 "detailed task list and task distribution in the README"）；且仓库 `task_list/` 只有 4 个族目录，SHW 任务散在 `autogen_tasks/primitive/`，与论文五族口径不一致 | **方案 a（不动目录结构）**：README 直接按论文五族口径列任务清单与分布；SHW 任务的代码位置如实标注为 `autogen_tasks/primitive/`（unscrew/weight/pill 系列）+ `task_list/` 相关任务。目录归位与否留到后续单独评估。**实施进度**：README 结构与 TODO 占位已就位；任务条目待用户补全后重新盘点计数、生成 `docs/TASKS.md` 并填入 README | 🔧 修复中（等任务条目补全） |
| 5 | README 缺 prompts 与推理设置索引（6ifo Q4 承诺读者能在 README 定位这些材料） | 新增 README 章节 "Code & documentation map"：4.1 prompts 索引（指向各节点 .py 内嵌 system prompt 的文件+位置，单一来源不复制内容）；4.2 节点设计文档（docs/Node/）；4.3 推理设置（重写后的 `pipeline/config.py` 环境变量与默认模型） | ✅ 已确定方案 |
| 13 | README 第 101 行路径错误：`scihorizon_elab/configs/` 不存在 | 改为正确表述：pipeline LLM 配置在 `scihorizon_elab/pipeline/config.py`，benchmark 任务配置在 `scihorizon_elab/benchmark/configs/` | ✅ 已确定方案 |
| 14 | README Citation 区块为空 | 补全 bibtex（等论文 camera-ready 定稿后填最终条目） | ✅ 已确定方案 |
| 15 | `third_party/` 与 `src/` 的 submodule 表述失实：`.gitmodules` 声明了 2 个 submodule 但实际都是普通 track 的目录，`git submodule update` 无效 | 暂不处理：`third_party/` 下的内容将来要清空并从远程仓库移除，届时 README 的 submodule 段落与 `.gitmodules` 一并处理 | ⏳ 待 third_party 清空时一并处理 |
