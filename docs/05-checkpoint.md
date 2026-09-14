# Checkpoint

Graph 在 `build_graph()` 中通过 `InMemorySaver` 编译。每次调用通过：

```python
{"configurable": {"thread_id": thread_id}}
```

指定 Thread。

- 相同 `thread_id`：继续已有 Graph State，消息上下文可累积。
- 不同 `thread_id`：State 隔离。
- Python 进程重启：InMemorySaver 内容丢失。

Checkpoint 不是长期记忆数据库；它首先解决 Graph State 的保存、恢复和可恢复执行。下一版再学习 PostgreSQL Checkpointer。
