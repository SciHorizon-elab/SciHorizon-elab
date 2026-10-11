#!/bin/bash
# 批量创建"抽屉存取"(任务表格WorkspaceInteraction.xlsx 第 5 页)任务
# 命名: 3_<Task name>，指令: Instruction 列
# 已存在的任务自动跳过；单任务 10 分钟超时

REPO_ROOT="/ssd/qinmaokai/workspace/SciHorizon-ELAB"
PY="/ssd/qinmaokai/.conda/envs/vlabench_2/bin/python"
SAVE_DIR="./benchmark/tasks/task_list/workspace_interaction/"
TARGET_DIR="$REPO_ROOT/scihorizon_elab/benchmark/tasks/task_list/workspace_interaction"
SUMMARY="$REPO_ROOT/batch_drawer_summary.txt"
PER_TASK_TIMEOUT=600

cd "$REPO_ROOT"

"$PY" - << 'EOF' > /tmp/drawer_tasks.tsv
import openpyxl
wb = openpyxl.load_workbook('/ssd/qinmaokai/workspace/SciHorizon-ELAB/docs/任务表格WorkspaceInteraction.xlsx')
ws = wb['抽屉存取']
for row in ws.iter_rows(min_row=5, values_only=True):
    if row[0] and row[2]:
        print(f"{row[0]}\t{row[2]}")
EOF

echo "Batch started: $(date)" > "$SUMMARY"

total=0; ok=0; skip=0; fail=0
while IFS=$'\t' read -r name instruction; do
    total=$((total+1))
    task_name="3_${name}"
    if [ -f "$TARGET_DIR/${task_name}_series.py" ]; then
        skip=$((skip+1))
        echo "[SKIP] $task_name (already exists)" | tee -a "$SUMMARY"
        continue
    fi
    echo "[RUN ] $task_name : $instruction" | tee -a "$SUMMARY"
    if MUJOCO_GL=egl timeout $PER_TASK_TIMEOUT "$PY" -m scihorizon_elab.pipeline.create_task \
        "$instruction" \
        --task-name "$task_name" \
        --save-dir "$SAVE_DIR" \
        > "/tmp/batch_${task_name}.log" 2>&1; then
        ok=$((ok+1))
        echo "[ OK ] $task_name" | tee -a "$SUMMARY"
    else
        fail=$((fail+1))
        echo "[FAIL] $task_name (exit $?) — see /tmp/batch_${task_name}.log" | tee -a "$SUMMARY"
    fi
done < /tmp/drawer_tasks.tsv

echo "----------------------------------------" | tee -a "$SUMMARY"
echo "Batch finished: $(date)" | tee -a "$SUMMARY"
echo "Total: $total  OK: $ok  Skipped: $skip  Failed: $fail" | tee -a "$SUMMARY"