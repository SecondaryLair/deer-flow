# 优化 Langfuse Traces 支持深度调研工具的两阶段追踪

## 背景

在深度调研工具（Deep Research Tool）的使用过程中，发现一个业务事务会包含两个独立的请求：

1. **调研阶段（Survey Phase）**：生成调查指南，询问用户是否继续
2. **报告阶段（Report Phase）**：用户接受调研计划后，生成最终报告

之前使用单一的 `main-<trace_id>` 命名方式，无法区分这两个不同的阶段，影响了可观测性和指标分析。

## 目标

将 langfuse traces 的命名方式从单一的 `main-<trace_id>` 改为：
- `survey-<trace_id>` - 调研阶段
- `report-<trace_id>` - 报告阶段

## 实现方案

### 1. 阶段判断逻辑

根据 `ChatRequest` 的参数判断当前处于哪个阶段：

```python
is_report_phase = (
    request.auto_accepted_plan or
    (request.interrupt_feedback and request.interrupt_feedback.upper().startswith("[ACCEPTED]"))
)
```

**判断规则：**
- **调研阶段**: `auto_accepted_plan=False` 且没有 `interrupt_feedback`
- **报告阶段**: `auto_accepted_plan=True` 或者 `interrupt_feedback` 以 `[ACCEPTED]` 开头

### 2. 代码修改

在 `src/deerflowx/server/app.py` 的 `_execute_workflow_with_langfuse` 函数中：

```python
# 根据请求类型确定 trace 名称
is_report_phase = (
    request.auto_accepted_plan or
    (request.interrupt_feedback and request.interrupt_feedback.upper().startswith("[ACCEPTED]"))
)

trace_name = f"report-{thread_id}" if is_report_phase else f"survey-{thread_id}"

with langfuse_client.start_as_current_span(name=trace_name) as span:
    span.update_trace(
        input={
            "messages": request.model_dump()["messages"],
            "enable_deep_thinking": request.enable_deep_thinking,
            "report_style": request.report_style.value,
            "enable_background_investigation": request.enable_background_investigation,
            "auto_accepted_plan": request.auto_accepted_plan,
            "interrupt_feedback": request.interrupt_feedback,
            "phase": "report" if is_report_phase else "survey",
        },
        session_id=thread_id,
        user_id="deerflow-user",
        tags=["research", "langgraph", "deepresearch", "report" if is_report_phase else "survey"],
    )
```

### 3. 增强的 Trace 信息

除了修改 trace 名称外，还在 trace 中增加了以下信息：

- `phase`: 明确标识当前阶段（"survey" 或 "report"）
- `auto_accepted_plan`: 是否自动接受计划
- `interrupt_feedback`: 用户的中断反馈
- 在 `tags` 中增加阶段标签

### 4. 测试验证

添加了单元测试来验证 trace 名称的判断逻辑：

```python
class TestLangfuseTraceNaming:
    def test_trace_name_determination_survey_phase(self):
        # 测试调研阶段的 trace 名称确定逻辑

    def test_trace_name_determination_report_phase_accepted(self):
        # 测试报告阶段的 trace 名称确定逻辑 (用户接受计划)

    def test_trace_name_determination_report_phase_auto_accepted(self):
        # 测试报告阶段的 trace 名称确定逻辑 (自动接受计划)
```

## 效果

### 优化前
- 所有请求都使用 `main-<trace_id>` 命名
- 无法区分调研和报告阶段
- 难以进行针对性的性能分析

### 优化后
- 调研阶段：`survey-<trace_id>`
- 报告阶段：`report-<trace_id>`
- 可以分别分析两个阶段的性能指标
- 更清晰的可观测性和调试体验

## 使用示例

### 调研阶段 Trace
```
Name: survey-abc123
Phase: survey
Tags: ["research", "langgraph", "deepresearch", "survey"]
Input: {
  "auto_accepted_plan": false,
  "interrupt_feedback": null,
  "phase": "survey"
}
```

### 报告阶段 Trace
```
Name: report-abc123
Phase: report
Tags: ["research", "langgraph", "deepresearch", "report"]
Input: {
  "auto_accepted_plan": false,
  "interrupt_feedback": "[ACCEPTED] 开始研究",
  "phase": "report"
}
```

## 兼容性

- 不影响现有的 langfuse 集成
- 向后兼容，不需要修改其他组件
- 测试覆盖率保持在 49.90%

## 总结

这次优化成功实现了深度调研工具两阶段的独立追踪，提升了系统的可观测性。通过区分调研和报告阶段，可以更好地分析和优化各个阶段的性能，为后续的系统优化提供更精确的数据支持。