"""
工具执行外壳

创建时间：2026/4/28
开发人：zcry
"""

#TODO: 这个文件最关键，它相当于你工具层的 harness。建议它负责：
# 参数校验
# before/after tool hook
# observer 埋点
# duration 统计
# 工具异常捕获
# 把异常转换成 ToolResult
# 以后 agent 不直接调 tool.ainvoke(...)，而是走 ToolRuntime.invoke(...)。