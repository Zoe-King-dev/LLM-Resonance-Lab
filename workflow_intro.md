典型工作流（30 分钟版）

  按 PRD 的成功标准：

  1. 浏览题库 — python run.py cases
  2. 跑 A 组 — python run.py run --mock（约 1 分钟）
  3. 挑一个做盲测 — python run.py blind case_001 --seed 1
  4. 打开 blind/case_001/response_A.md 和
  response_B.md，不知道谁是哪个模型
  5. 凭感觉选 A/B/Tie（不看 mapping.json）
  6. 生成评估模板 — python run.py eval case_001，填 6 维度分数
  7. 跑 B 组 — python run.py marathon career_choice --model <name>
  --mock
  8. 记录感受 — python run.py journal note "..."
  9. 打开 mapping.json，看看你的判断对不对
  10. 重复几次，让直觉沉淀

  最终你回答的是"哪个模型最懂我"，而不是"哪个模型最强"。