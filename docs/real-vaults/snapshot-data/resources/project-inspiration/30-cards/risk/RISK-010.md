---
id: RISK-010
type: RISK
status: active
version: '1.0'
digest: sha256:900b989ebb44dad1
created: '2026-10-01'
risk_type: methodological
severity: high
prj_refs:
- PRJ-021
related_ptns:
- PTN-025
---
## 数字孪生不保真导致虚假信心（Simulation Fidelity Gap）

**触发条件：** 在合成环境/数字孪生中做政策/规则/Agent 行为预演，但模拟环境的 Agent 行为模型、校准方法、真实系统拟合误差未经验证。

**后果：** "在模拟器里很安全"的结论被带到真实部署，实际二阶行为（herding、操纵、级联失败）与模拟完全不同，产生虚假信心。

**缓解：** 必须对历史危机/已知事故做回测校准；公开拟合误差；模拟结论标注"仅在模拟假设下成立"；不能用模拟结果替代真实灰度发布。
