# Course Energy Planner · 课程与精力规划

一个为 Codex 准备的学习规划 Skill：整合课表与作业，按照截止时间、实际进度和个人精力安排工作。

它关注的是一份能开始、能调整的计划：你每天能投入多久、哪些任务启动困难、哪些适合连续做，以及做完后真实花了多少时间。

## 可以做什么

- 汇总多个课程来源，区分正式 DDL、个人提前完成目标和待核实信息。
- 估算剩余工作与资源需求，优先采用你的实际耗时。
- 为大项目安排可验收的节点，为阅读提供聚焦问题、限时和停止条件。
- 根据工作习惯安排连续工作块或不同类型任务之间的切换。
- 给出材料链接、具体第一步和完成标准，减少启动时需要做的决定。
- 按需指导制作周日历、甘特图和可勾选看板，并保留完成记录。

每天的工作上限、起床时间和任务偏好都需要根据使用者调整；示例数据完全虚构。

## 安装

在 Codex 中发送：

> 请用 $skill-installer 从 https://github.com/ususakura/course-energy-planner/tree/main/course-energy-planner 安装这个 Skill，并确认能识别。

也可以点击本仓库的 **Code → Download ZIP**，解压后在 Codex 中打开文件夹，再发送：

> 请将这里的 course-energy-planner 文件夹安装到当前版本的用户级 skills 目录，并确认能够调用。

注意选择直接包含 `SKILL.md` 的内层文件夹。Codex 通常会自动识别新安装的 Skill；如果没有出现，重启后再试。参见 [OpenAI 官方 Skill 说明](https://learn.chatgpt.com/docs/build-skills)。

## 第一次使用

发送下面这段，并附上手头已有的课表截图、作业链接或文字：

> 请用 $course-energy-planner 帮我整理课程和作业。先确认待办、截止时间和剩余工作，再结合我的习惯安排未来两周。缺少的信息一次问我一个简单问题。

可以逐步告诉它：

- 哪些任务已经完成、哪些还没开始。
- 每天大概能投入多久，是否把上课算进去。
- 哪些任务难启动，哪些喜欢连续做完。
- 实际耗时、今天的精力和临时安排。

不需要先把所有资料整理完。后续直接说“这个做完了”“实际用了两小时”“今天需要轻一点”，让它更新计划。

需要可视化时，可以说：

> 请把课程和任务放进同一个周日历，并增加项目甘特图。点击任务可以看详情和材料，完成后可以勾选。布局紧凑，尽量一屏看完全天安排。

## 日历联动（含 Google Calendar）

可以以你指定的外部日历为准：先读取已有约定和手动调整，再更新周计划与看板。保留完成记录、材料和休息空档，避免重复创建日程。Google Calendar 另提供账号与日历选择、时区、重复课程及同步失败处理指南。

开始时可以说：

> 请用 $course-energy-planner 联动我的 Google Calendar。先读取未来两周安排，以我在日历里手动调整的时间为准，更新周计划。把建议工作时段写入我指定的学习日历，保留完成记录和材料链接；目标日历不明确时再问我。

[查看 Google Calendar 联动指南](course-energy-planner/references/google-calendar.md)。安装 Skill 本身不会建立账号连接或启动后台同步；读取、写入和定时更新取决于你授权的工具与实际配置。一次性 `.ics` 导入也不等于双向同步。

## 使用边界

这是可复用的规划方法，不是已经部署好的网站。网页、持久存储和定时维护需要另行配置，并取决于当前环境可用的工具。它不会仅因安装就自动读取学校账号、运行提醒或提交作业。课程来源需要你提供并授权访问；无法核实的内容会保留为待确认。

## 文件

- `course-energy-planner/SKILL.md`：主要工作方法。
- `course-energy-planner/references/data-and-updates.md`：共享视图、完成记录和持续更新规则。
- `course-energy-planner/references/google-calendar.md`：Google Calendar 联动与能力边界。
- `course-energy-planner/assets/example-plan.json`：虚构的结构化计划示例。
- `course-energy-planner/scripts/check_plan.py`：只读检查时间冲突、容量和安排缺口。

可选检查（Python 3.9+，仅使用标准库）：

```sh
python3 course-energy-planner/scripts/check_plan.py course-energy-planner/assets/example-plan.json
```

退出码 `0` 表示没有结构或硬约束错误，但仍可能有未排入警告；`1` 表示时间冲突、超出容量或安排在截止后；`2` 表示输入无效。它不替你决定跳过任务。
