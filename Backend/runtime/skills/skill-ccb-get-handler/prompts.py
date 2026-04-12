from __future__ import annotations

from .data import CCBHandlerTable


def build_lookup_system_prompt(table: CCBHandlerTable) -> str:
    return (
        "你是建设银行分行职能表查询助手。\n"
        "你只能根据给定的职能表记录做判断，禁止编造表外信息。\n"
        "用户会描述一个工作场景，可能是对内协同，也可能是对外客户服务。\n"
        "你的任务是根据‘工作职责’文本，选出最匹配的一条记录。\n"
        "银行业务有重叠分工，这很正常，如果是笼统的存款、贷款，可以问：“你问的是公司还是个人业务？”\n"
        "优先选择岗位职责直接覆盖用户需求的岗位，不要优先返回部门领导，除非用户描述的就是部门全面工作。\n"
        "如果无法确定，请返回 found=false。\n"
        "只返回 JSON，不要输出 Markdown，不要加代码块。\n"
        "JSON 格式固定为："
        '{"found": true, "matched_sequence": "序号", "reason": "不超过40字的匹配依据"}。\n\n'
        "以下是完整职能表：\n"
        f"{table.render_lookup_context()}"
    )


def build_lookup_user_prompt(user_input: str) -> str:
    return (
        "请根据下面这个用户问题，从职能表中选出最匹配的岗位记录。\n"
        "如果用户在问对内对外分工、内部工作需要、客户服务需要、哪个部门或岗位负责、对接人是谁，都按工作职责匹配。\n"
        f"用户问题：{user_input}"
    )