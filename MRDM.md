# Minimal Rhythm Dynamics Model (MRDM)

Version: v0.3 Draft

---

# 1. Purpose

MRDM（Minimal Rhythm Dynamics Model）旨在构建一个可长期执行（> 6个月）、单被试（N=1）、极低记录成本的人类行动节律动力学模型。

核心原则：
> 牺牲微观预测精度，换取系统在现实中连续运行一年的生命力。

目标并非优化单日生产力或效率，而是：
研究并构建具有稳定吸引子、快速恢复能力和长期可持续性的行动节律系统。

---

# 2. System Boundary

研究对象：人类行动节律系统（Human Action Rhythm System）

**不研究：**
- 具体任务执行与生产力（效率）
- 精神疾病本身
- 长期人生目标或价值观

**仅研究：**
- 睡眠与觉醒的物理时间分布
- 系统行为的惯性（势阱）
- 扰动后的节律恢复能力

---

# 3. Objective Function

本系统不再与“高质量行动时间”挂钩，回归纯粹的节律稳定性。

系统目标函数：

$$
J = -\beta Var(P) - \gamma D - \eta R
$$

其中：
- $Var(P)$：长期相位偏移的方差（节律波动越小越好）。
- $D$：累计睡眠债（长期疲劳度越低越好）。
- $R$：扰动后的恢复时间（系统韧性越强越好）。

优化目标即为使 $J$ 最大化（或惩罚项最小化）。

---

# 4. State Variables (Fast & Slow)

系统状态：

$$
X_t = \begin{bmatrix} P_t \\ D_t \\ H_t \end{bmatrix}
$$

## S1. Circadian Phase (P) - 慢变量

生物钟相对于目标节律的偏移程度。

$$
P_t = Wake_t - Wake_{target}
$$

单位：hour

## S2. Sleep Debt (D) - 慢变量

系统累计的生理恢复需求，具有积分效应。

$$
D_t = \lambda D_{t-1} + (SleepNeed - SleepActual)
$$

其中建议 $\lambda = 0.9$。

## S3. Habit Strength (H) - 慢变量 (Asymmetric)

行为惯性，即当前节律吸引子的势阱深度。
现实中，建立习惯极其缓慢，而破坏习惯只需一瞬间。因此引入非对称演化：

$$
H_t = 
\begin{cases} 
\alpha_{up} H_{t-1} + (1 - \alpha_{up}), & |P_t| < 1h \\ 
\alpha_{down} H_{t-1}, & otherwise 
\end{cases}
$$

参数建议：
- $\alpha_{up} = 0.98$（缓慢爬坡：连续数周才能将势阱建立到 $H \rightarrow 1$）
- $\alpha_{down} = 0.50$（快速跌落：一两次熬夜通宵就会让 $H$ 迅速衰减）

取值范围：$0 \le H \le 1$

---

# 5. The "Zero-Cost" Observation Protocol

为了对抗观察者效应，确保系统不因记录繁琐而崩溃，所有观测变量的采集必须遵循**“每天主动思考不超过10秒”**的原则。

### 5.1 Rhythm Day (节律日)

为支持午睡、补觉和分段睡眠，统计单元不再严格等于自然日，而是以 `Wake Target` 为锚点的节律日。

- 先区分“主睡眠段”和“短睡眠段”：连续睡眠时长达到主睡眠阈值的记录视为主睡眠段，短于阈值的记录视为午睡或补觉段。
- 睡眠段是否属于某个节律日，首先看其**入睡开始时间**相对于 `Wake Target`：开始于 `Wake Target` 之前的睡眠段，归入当日节律日；开始于 `Wake Target` 之后的睡眠段，归入下一节律日。
- 因此，早晨继续睡到 `Wake Target` 之后的补觉仍算作当天节律日；而傍晚或深夜才开始的睡眠段，算作下一日的能量输入。
- 同一节律日内的多段睡眠按区间时长求和。
- `P` 以该节律日内“主睡眠段”的结束时间计算，相位只对主节律偏移负责，不对午睡重复计数。

## Automated Variables (自动获取，0秒成本)

**O1. Wake Time (起床时间)**
**O2. Sleep Time (入睡时间)**
- 来源：手机屏幕时间记录、智能手表或睡眠监测App。无需主观回忆。

## Manual Variables (手动输入，10秒成本)

**O3. Daily Momentum (M)**
压缩掉无法建模的快变量（认知激活度、精力波动）。
取值范围 0 ~ 10，采用绝对物理感觉锚定，避免基线漂移：
- `10`：理想状态（自然醒来，无阻力进入行动，无疲惫感）
- `5`：普通状态（需要轻微强迫自己，有正常范围的波动）
- `0`：完全失控（极度疲劳，认知模糊，无法执行任何计划）

**O4. Disturbance Flag (DIS)**
重大外部扰动记录。
取值：$0 = 无，1 = 有$。
（如：通宵、生病、长途跨时区旅行）。

---

# 6. Control Inputs & Pharmacological Layer

系统控制量：

$$
U_t = \begin{bmatrix} WakeTarget \\ MorningReset \\ Medication \end{bmatrix}
$$

- **Wake Target (目标起床)**：固定值，非极特殊情况不更改。
- **Morning Reset (晨间重置)**：起床1小时内是否接受强光照射（1=是，0=否）。
- **Medication (药物干预)**：针对特定被试，药物是控制量而非扰动。采用极简 0/1 记录（$Med_S$ 促眠, $Med_W$ 促觉醒, $Med_C$ 镇静）。

---

# 7. Attractor & Robustness

**Attractor (吸引域) 定义：**
当满足 $|P| < 1h$ 且 $D < 5h$，并连续维持 7天 以上，系统即判定为 `IN ATTRACTOR`。

**Robustness (鲁棒性) 测度：**
当扰动发生（$DIS_t = 1$）导致系统脱离吸引域后，重新回到 `IN ATTRACTOR` 状态所需的自然日天数，即为恢复时间 $R$。

---

# 8. Future Work (Deferred to v0.5+)

以下概念在理论上正确，但由于当前测量成本过高或数据量不足，暂不引入核心计算：

1. **Phase Response Curve (PRC) 修正项**：晨间重置效应对相位的非线性拉扯（需要连续核心体温记录 $CBT_{min}$）。
2. **Control Cost (控制代价)**：在目标函数中加入 $-\delta \sum |U_t|$，以惩罚过度依赖强制唤醒或药物，由于 $\delta$ 权重目前只能靠猜，暂不引入。