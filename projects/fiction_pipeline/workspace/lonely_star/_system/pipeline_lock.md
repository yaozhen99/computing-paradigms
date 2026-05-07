# 第一卷管道锁：世外桃源

## 状态：运行中

## 当前阶段：worldbuilding（世界观补充）

## 输入文件
- 需求文档：`00_story_master/user_inputs/lonely_star_volume1.md`
- 世界观：`01_worldbuilding/worldbuilding.md`
- 不可更改设定：`01_worldbuilding/rewrite_spec.md`

## 管道流程

### 1. worldbuilding（当前）
- 任务：补充动植物、群居智慧生物、三大奇观感官细节、日常景色、异化生活方式细节
- 输入：worldbuilding.md + rewrite_spec.md + volume1需求
- 输出：worldbuilding.md 更新版
- 需人工审核

### 2. outline
- 任务：基于世界观+需求文档生成第一卷章节大纲
- 输入：worldbuilding.md + volume1需求
- 输出：02_outline/outline.md
- 需人工审核

### 3. chapter_plan
- 任务：每章详细计划
- 输出：03_chapter_plan/ 下每章一个文件

### 4. writing
- 任务：逐章撰写正文
- 输出：04_chapters/ 下每章一个文件

### 5. review
- 任务：设定自洽、风格一致、人物真实
- 输出：05_review/review_report.md

### 6. finalization
- 任务：终稿定稿
- 输出：06_final/

## 否决机制
- 任何阶段产出不符合要求，可否决打回
- 最多3次否决，超过则暂停管道等待人工介入
