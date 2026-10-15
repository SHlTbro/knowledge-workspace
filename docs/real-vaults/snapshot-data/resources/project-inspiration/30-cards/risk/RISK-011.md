---
id: RISK-011
type: RISK
status: active
version: '1.0'
digest: sha256:0dd653364966d4a5
created: '2026-10-01'
risk_type: trust
severity: medium
prj_refs:
- PRJ-028
related_ptns:
- PTN-032
---
## 不可篡改 ≠ 可信（Immutability ≠ Truth）

**触发条件：** 把"上链/不可篡改/attestation"当作内容可信的代名词，忽略最初记录的真实性和来源质量。

**后果：** 错误数据被永久记录且不可修改；confidence 被错误模型系统性抬高；trust score 很低的对象被当作可信来源；后续系统消费错误证据对象。

**缓解：** 区分"记录完整性"（不可篡改证明的）和"内容真实性"（需要独立验证）；attestation 必须包含来源和验证方法；定期 re-validate 证据对象；低 trust score 对象不能自动采信。
