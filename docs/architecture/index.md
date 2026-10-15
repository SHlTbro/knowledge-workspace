# 架构与协作方式

先看系统边界，再看实际可运行单元。MemberStore、BindingStore、Reader 和 Writer 是库模块，不是独立服务。

- [C4 Context](c4-context.md)
- [C4 Container](c4-containers.md)
- [蒸馏与消费流程](../../assets/diagrams/distillation.md)

未增加 Component：本次读者无需类级分解。未增加 Dynamic：实际正常/失败/恢复由 Workflow 说明。未增加 Deployment：预览不承诺云部署或生产接替。
