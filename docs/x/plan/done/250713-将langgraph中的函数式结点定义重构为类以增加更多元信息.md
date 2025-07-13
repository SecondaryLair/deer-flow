如:
```python

async def coder_node(state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )

```
重构为

```python

class Coder:

    @classmethod
    def name(cls) -> str:
        return "coder"

    @classmethod
    async def action(cls, state: State, config: RunnableConfig) -> Command[Literal["research_team"]]:
        """Coder node that do code analysis."""
        logger.info("Coder node is coding.")
        return await _setup_and_execute_agent_step(
            state,
            config,
            "coder",
            [python_repl_tool],
        )

```

调用形式为
```python
    builder.add_node(Coder.name(), Coder.action)
```

后续可以考虑抽象一个基类来限制所有Node继承该基类，并实现node和action方法, 以约束行为