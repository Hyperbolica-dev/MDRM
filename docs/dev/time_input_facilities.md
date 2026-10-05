# 时间录入设施调研

调研日期：2026-09-18

## 结论

MRDM 的睡眠时间字段需要的是“仅时间、低摩擦、可预测”的输入，而不是泛化的日期时间自然语言解析。当前实现保留文本框入口，用标准库 Unicode NFKC 先统一全角/半角，再按明确规则转换为 `HH:MM`；录入、CSV 导入、原始数据保存、动力学解析和干预记录共用同一规范化函数。

支持的典型输入包括：

- `08:30`、`8:3`
- `830`、`8`
- `８：３０`
- `8点半`、`8点30分`
- `8pm`、`下午8点`

所有成功输入最终保存为 `HH:MM`。日期、时区和相对时间不在此字段内解析；无效时间不会被猜测。

## 已有设施比较

| 设施 | 能力 | 对 MRDM 的适配性 | 处理决定 |
|---|---|---|---|
| Streamlit `st.time_input` | 原生时间控件，返回 `datetime.time`，可指定 24 小时显示和步长 | 能保证值类型，但键盘输入和显示受浏览器/区域设置影响；不负责把全角或 `830` 统一为 `HH:MM` | 作为已有的干预/参数控件继续使用；睡眠快速录入保留可规范化文本入口 |
| Python `unicodedata.normalize("NFKC")` | 标准库兼容性规范化，可处理全角数字和全角标点 | 直接解决全角/半角问题，无新增依赖 | 采用 |
| `dateutil.parser` | 宽松日期时间解析，可处理多种日期时间格式 | 语义过宽，可能接受日期、模糊日期顺序和时区；不适合仅时间的睡眠字段 | 不采用 |
| `dateparser` | 更广的多语言、相对日期和自然语言解析 | 依赖更重且会引入“昨天/两小时后”等当前字段不需要的语义 | 不采用 |
| Plotly `connectgaps=True` | 折线在 `None`/`NaN` 数据处继续连接 | 与 Core Trend Charts 的断点问题一一对应 | 采用 |

## 参考资料

- [Streamlit `st.time_input`](https://docs.streamlit.io/develop/api-reference/widgets/st.time_input)
- [Streamlit forms 与回调限制](https://docs.streamlit.io/develop/concepts/architecture/forms)
- [Python Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [Python `unicodedata.normalize`](https://docs.python.org/3/library/unicodedata.html)
- [`dateutil.parser` 文档](https://dateutil.readthedocs.io/en/stable/parser.html)
- [`dateparser` 文档](https://dateparser.readthedocs.io/en/stable/index.html)
- [Plotly 折线图的 `connectgaps`](https://plotly.com/python/line-charts/)
