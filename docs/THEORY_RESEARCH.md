# MRDM Closed-Loop Control Theory Research

Version: v0.5 (research draft)

本文件将 MRDM 从被动状态观测器（v0.4）升级为主动反馈控制器的理论基础。核心工具是 Khalsa et al. (2003) 的人类昼夜节律光 Phase Response Curve (PRC)，配合隐式估算的 $CBT_{\min}$，实现零额外记录摩擦（< 10 秒/天）的光疗干预建议。

---

# 1. 控制框架：从观测到反馈

v0.4 的 MRDM 是开环观测器：记录 $(P, D, H)$ 并诊断吸引子状态，但不对状态施加控制。

v0.5 引入闭环结构：

$$
X_{t+1} = f(X_t, U_t)
$$

$$
U_t = g(X_t)
$$

- $X_t = (P_t, D_t, H_t)$：状态向量
- $U_t$：控制输入，本阶段仅含光疗时段 $T_{light}$（Morning Reset 升级为带时刻的光窗口）
- $f$：MRDM 动力学（MRDM.md §4）
- $g$：控制律（本文 §3）

控制目标与 MRDM.md §3 的目标函数一致：最小化 $Var(P)$ 与 $D$，缩短扰动恢复时间 $R$。

---

# 2. 隐式 $CBT_{\min}$ 估算（零摩擦观测）

经典 PRC 需要以核心体温最低点 $CBT_{\min}$ 为相位原点，而 $CBT_{\min}$ 需要连续直肠/植入式测量，违反 10 秒记录约束。

## 2.1 估算公式

利用中睡时间 (Mid-Sleep Time, MSM) 与 $CBT_{\min}$ 的稳定相位关系：

$$
MSM = T_{wake} - \frac{SleepDuration}{2}
$$

$$
\widehat{CBT}_{\min} = MSM + 1.5\ \text{hours}
$$

其中 $T_{wake}$ 与 $SleepDuration$ 全部来自现有观测（自动变量 O1/O2），**无需任何新增输入**。

## 2.2 相位折叠

$MSM$、$\widehat{CBT}_{\min}$ 均折叠到 $[-12, 12)$ 小时区间，以保证跨午夜的 24 小时环状正确性：

$$
\widehat{CBT}_{\min} \leftarrow \widehat{CBT}_{\min} - 24\lfloor (\widehat{CBT}_{\min} + 12)/24 \rfloor
$$

## 2.3 极端扰动下的 MSM 鲁棒性

### 通宵（SleepDuration = 0）
MRDM.md §S1 规定 $P_t = \text{None}$，$MSM$ 未定义。此时 $CBT_{\min}$ 也标记为不可估，光疗建议暂停并转入"债务恢复模式"（全额 $SleepNeed$ 入债，$H$ 快速衰减），直至下一次完整主睡眠段提供有效 $MSM$。

### 社会性时差 / 熬夜
当 $P$ 漂移超过 ±6h（接近半周期），折叠语义需注意：$P = M_{actual} - M_{target}$ 折叠到 $[-12, 12)$ 会造成 ±12h 处的符号歧义（如 $P=+11$ 与 $P=-13$ 等价）。此时应以 $|P| \le 6h$ 为有效控制区，超出部分视为"不确定相位"，优先通过睡眠窗约束而非光疗纠正。相位折叠方向应与最近的目标唤醒时间一致，避免 12h 处的跳变误判。

### 结论
在正常观测（主睡眠段存在）与中等扰动（$|P| \le 6h$）条件下，$\widehat{CBT}_{\min}$ 可稳定驱动 PRC 控制。极端扰动退化为安全模式，不做光疗干预。

---

# 3. Khalsa (2003) 连续 PRC 控制律

## 3.1 PRC 数学形式

以 $\widehat{CBT}_{\min}$ 为相位原点 $0$，定义相位角：

$$
\Delta\phi = T_{light} - \widehat{CBT}_{\min} \in [-12, 12)
$$

连续正弦 PRC（幅度由光强饱和缩放）：

$$
f(\Delta\phi) =
\begin{cases}
0, & |\Delta\phi| > 6 \\
-A \cdot \sin\left(\dfrac{\pi \Delta\phi}{6}\right), & |\Delta\phi| \le 6
\end{cases}
$$

$$
A = \min\left(1.2\,\text{h},\ 1.2\,\text{h} \cdot \frac{lux}{10000}\right)
$$

符号约定：
- **延迟区** $\Delta\phi \in [-6, 0)$：$f > 0$，相位右移（$P$ 增大）
- **提前区** $\Delta\phi \in (0, 6]$：$f < 0$，相位左移（$P$ 减小）
- **死区** $\Delta\phi = 0$：$f = 0$

峰值响应位于 $\Delta\phi = \pm 3\,\text{h}$（延迟 $+1.2\text{h}$ / 提前 $-1.2\text{h}$），对应 Khalsa (2003) 观测到的 $CBT_{\min}$ 前 2–4h（延迟）与后 2–4h（提前）敏感窗。边界 $\pm 6\,\text{h}$ 处归零，代表白天光对相位几乎无影响。

## 3.2 比例控制律

为避免固定峰值光导致的恒定步长与过冲，采用**比例控制 + deadband**：

$$
U_t = g(P_t) =
\begin{cases}
T_{light} = \widehat{CBT}_{\min} + 3 \cdot \min\!\left(1,\ \dfrac{P_t - \delta}{2}\right), & P_t > \delta \\[6pt]
T_{light} = \widehat{CBT}_{\min} - 3 \cdot \min\!\left(1,\ \dfrac{|P_t| - \delta}{2}\right), & P_t < -\delta \\[6pt]
\varnothing\ (\text{无光}), & |P_t| \le \delta
\end{cases}
$$

- $\delta = 0.5\,\text{h}$：deadband，|P| 进入此范围停止干预，避免极限环振荡
- offset 上限 3h（PRC 峰值），随偏差 $|P| - \delta$ 线性缩放到 0
- 相位偏差大时接近峰值窗口（快速收敛），偏差小时偏离峰值（PRC 输出渐小 → 平滑逼近，无过冲）

## 3.3 状态更新

$$
P_{t+1} = P_t + f(\Delta\phi_t) + \eta P_t
$$

$$
D_{t+1} = \lambda_d D_t - k D_t \left(1 - e^{-(S_t - N)/\tau}\right),\quad S_t = N + \min(2, 0.3 D_t)
$$

- $\eta$：无光时的自然相位松弛率（模拟中取 $-0.1/\text{day}$，代表弱环境光夹持；光疗场景 $\eta=0$）
- 参数沿用 config.yaml：$\lambda_d=0.9$，$k=0.4$，$\tau=2.0$，$N=7.0\text{h}$，$WakeTarget=08:30$

---

# 4. 状态空间分区与干预规则

$(P, D)$ 平面映射为确定性控制规则：

| 区域 | $P$ 范围 | $D$ 范围 | 干预规则 |
|---|---|---|---|
| A. 稳态锁定 | $\|P\| \le 1.0$ | $D \le 2.0$ | 无干预，维持现律 |
| B. 相位延迟（社会性时差） | $P > 1.0$ | $D \le 5.0$ | 晨间光：$T_{light} = \widehat{CBT}_{\min} + 3\,\text{h}$（提前） |
| C. 相位提前 | $P < -1.0$ | $D \le 5.0$ | 傍晚光：$T_{light} = \widehat{CBT}_{\min} - 3\,\text{h}$（延迟） |
| D. 急性睡眠债 | $\|P\| \le 1.0$ | $D > 5.0$ | 延长睡眠窗（补债优先），光疗辅助 |
| E. 复合扰动 | $\|P\| > 1.0$ | $D > 5.0$ | 双通道：债务恢复 + 相位光疗（§3.2） |
| F. 不确定相位 | $\|P\| > 6.0$ 或 $P=\text{None}$ | 任意 | 禁光疗，仅睡眠窗约束 |

> 吸引域判定采用本阶段任务定义：$|P| \le 1.0,\ D \le 2.0$（比 MRDM.md §7 的 $D<5$ 更严，用于控制验证）。

---

# 5. 仿真验证

## 5.1 实验设定

- 窗口：7 个节律日
- 光强：$lux = 10000$（≈ 晨光 / 治疗灯箱），$A = 1.2\,\text{h}$
- 场景 ①：社会性时差 $P=+3.0,\ D=4.0$，晨间光
- 场景 ②：严重剥夺 / 早醒 $P=-3.0,\ D=6.0$，傍晚光
- 场景 ③：对照 $P=+3.0,\ D=4.0$，无光（$\eta=-0.1$）

## 5.2 轨迹输出

```
Scenario 1: Social Jetlag (P=+3.0, D=4.0) morning light
day 0  P=  3.00  D=  4.00
day 1  P=  1.80  D=  2.88
day 2  P=  0.78  D=  2.19
day 3  P=  0.52  D=  1.72 *   <- 进入吸引域
day 4  P=  0.50  D=  1.39 *
day 5  P=  0.50  D=  1.15 *
day 6  P=  0.50  D=  0.96 *
day 7  P=  0.50  D=  0.81 *
converged day 3

Scenario 2: Severe Deprivation (P=-3.0, D=6.0) evening light
day 0  P= -3.00  D=  6.00
day 1  P= -1.80  D=  3.98
day 2  P= -0.78  D=  2.86
day 3  P= -0.52  D=  2.18
day 4  P= -0.50  D=  1.72 *   <- 进入吸引域
day 5  P= -0.50  D=  1.39 *
day 6  P= -0.50  D=  1.15 *
day 7  P= -0.50  D=  0.96 *
converged day 4

Scenario 3: Control (P=+3.0, D=4.0) no light
day 0  P=  3.00  D=  4.00
day 1  P=  2.70  D=  2.88
day 2  P=  2.43  D=  2.19
day 3  P=  2.19  D=  1.72
day 4  P=  1.97  D=  1.39
day 5  P=  1.77  D=  1.15
day 6  P=  1.59  D=  0.96
day 7  P=  1.43  D=  0.81
not converged in window
```

## 5.3 验证结论

1. **非线性确认**：场景 ① ΔP 步长逐日递减（−1.20 → −1.02 → −0.26 → −0.02），比例控制 + 连续正弦 PRC 产生渐近收敛曲线，无恒定线性步长；D 呈饱和指数衰减。
2. **收敛加速**：场景 ① 第 3 天、场景 ② 第 4 天进入吸引域（$|P|\le1.0, D\le2.0$）；对照 ③ 第 7 天 $P=1.43$ 仍在外，证明光疗是 $P$ 收敛的必要加速器。
3. **无过冲**：deadband $\delta=0.5$ 内停止干预，$P$ 平滑停在 0.50，无极限环。
4. **符号正确性**：晨间光（$\Delta\phi>0$）驱动 $P$ 左移，傍晚光（$\Delta\phi<0$）驱动 $P$ 右移，与 Khalsa (2003) 一致。

---

# 6. 对 v0.5 的实现建议

1. **新增控制函数**（已实现于 `model/dynamics.py`）：
   - `estimate_cbt_min(wake, sleep)`：$MSM + 1.5$，零摩擦
   - `prc_shift(cbt_min, light_hour, lux)`：连续正弦 Khalsa PRC
2. **控制律**（`scripts/simulate_control.py`）：比例 + deadband，晨/晚光窗口锚定相对 $\widehat{CBT}_{\min}$
3. **UI 集成**（后续）：在仪表盘显示"今日光疗建议窗口" $[T_{light} \pm 0.5]$，记录用户是否执行（0/1，延续 Morning Reset 语义），不新增摩擦
4. **参数待实验标定**：$A$ 的 lux 饱和曲线、$\eta$（自然松弛）、deadband $\delta$，需 N=1 实测数据拟合

---

# 7. 文献索引

| Reference | Key Insight | Impact on MRDM |
|---|---|---|
| Khalsa et al. (2003) | 人类单次亮光 PRC：延迟峰值在 CBT_min 前 2–4h，提前峰值在后 2–4h，幅度 ~1.0–1.5h | 定义 $\widehat{CBT}_{\min}$ 原点与连续正弦 PRC $f(\Delta\phi)$，驱动光疗控制律 |
| Van Dongen et al. (2003) | 慢性限制的认知缺陷等价于总剥夺 | 支持 D 的比例恢复，而非一次性还清 |
| Banks & Dinges (2010) | 1–2 夜恢复睡眠不足 | 多夜比例衰减 $k=0.4$ |
| Ochab et al. (2021) | 睡眠债恢复呈指数衰减 | 直接支撑 $D_t$ 饱和指数公式 |
| Yamazaki et al. (2021) | 单次恢复睡眠不足以消除累计缺陷 | 多夜恢复，与光疗控制窗口正交执行 |

详见 `reference/khalsa2003.md` 及各文献卡片。
