---
name: skill-ccb-get-handler
description: 'Use when asking which internal department, role, or owner in the branch should handle a responsibility, internal interface, or office number lookup based on the handler table.'
---

# CCB Get Handler Skill

## Purpose
根据分行职能表，按工作职责匹配最合适的内部职能部门、岗位负责人链条和办公号码。

## Use When
- 用户在问分行内部某项工作由哪个部门、哪个岗位、哪个负责人承接。
- 用户在问对内对外工作分工、内部协同分工、行内接口人、办公号码。
- 用户的问题目标是“在行内找谁对接”，而不是去找银行外部机构。

## Avoid When
- 用户在问外部保险公司客服、外部律师、监管投诉热线、实体网点地址等银行外部机构问题。
- 用户只是泛泛问“保险业务找谁”“贷款找谁”，但没有分行内部职能语境。
- 用户要的是普适建议，而不是内部岗位职责映射。

## Input Contract
- 输入是标准 `AgentRequest`。
- 技能会读取 `data/ccb_handler_table.csv` 作为唯一职能依据。

## Output Contract
固定输出五行：
- 职能部门：**
- 岗位：**岗
- 负责人链条：姓名（职务）—姓名（职务）—姓名（**岗）
- 工作职责：直接输出该 **岗 的简短工作职责摘要
- 联系方式：仅给岗位负责人的办公号码。

## Runtime Notes
- 当前由 LLM 主路由决定是否调用本技能，不存在针对本技能的关键词快脑。
- 第一版是“全表进上下文 + LLM 按职责匹配”的实现，不是 RAG。
- 如果匹配不确定，技能返回未找到明确匹配，而不是编造表外信息。
- 联系方式只输出岗位负责人办公号码，不扩展到其他外部电话。