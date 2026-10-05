from uuid import uuid4
import sqlite3

import pandas as pd
import streamlit as st

from model.medication_journal import read_medication_library, read_medication_journal, save_medication_event


def render_medication_journal(profile_id, associated_day, read_only, chinese):
    with st.expander("药物记录：可选详情 · 仅本地" if chinese else "Medication journal: optional details · local only"):
        st.caption("日常只需上方勾选。这里可用代号记录，名称之外都可留空；不联网、不跳转百科，不会自动改写睡眠标记。" if chinese else "The checkbox above is sufficient. Details can use an alias and stay local; saving here does not change the sleep checkbox.")
        if read_only:
            st.info("示例档案不读取或保存个人药物日志。" if chinese else "Sample profiles cannot access the personal journal.")
            return
        path = f"data/private/{profile_id}/medication.sqlite3"
        generation_key = f"medication_generation:{profile_id}"
        if generation_key not in st.session_state:
            st.session_state[generation_key] = str(uuid4())
        event_id = st.session_state[generation_key]
        with st.form(f"medication:{profile_id}:{event_id}"):
            choices = [label for _, label in read_medication_library(path)]
            chosen = st.selectbox("常用名称或代号" if chinese else "Saved name or alias", [""] + choices)
            new_label = st.text_input("新名称或代号（首次填写）" if chinese else "New name or alias (first use)")
            day = st.date_input("关联睡眠日期" if chinese else "Associated sleep date", value=associated_day)
            dose = st.text_input("实际用量（可空，如半片）" if chinese else "Amount used (optional, e.g. half a tablet)")
            clock = st.text_input("服用钟点（可空，HH:MM）" if chinese else "Clock time used (optional, HH:MM)")
            st.caption("钟点不确定就留空；关联睡眠日期不等于服用日期，本版不据此重建精确服用时刻。" if chinese else "Leave unknown time blank. Associated sleep date is not the administration date; no exact timestamp is inferred.")
            note = st.text_input("备注（可空）" if chinese else "Note (optional)")
            save = st.form_submit_button("保存本地药物记录" if chinese else "Save local medication entry")
        if save:
            try:
                save_medication_event(path, event_id, day, new_label or chosen, dose, clock, note)
                st.session_state[generation_key] = str(uuid4())
                st.session_state[f"medication_receipt:{profile_id}"] = True
                st.rerun()
            except (ValueError, OSError, sqlite3.Error) as error:
                st.error(str(error))
        if st.session_state.pop(f"medication_receipt:{profile_id}", False):
            st.success("已保存本地药物记录。" if chinese else "Saved locally.")
        if st.checkbox("显示本地日志" if chinese else "Show local journal", key=f"show_medication:{profile_id}"):
            rows = read_medication_journal(path)
            st.dataframe(pd.DataFrame(rows, columns=["关联日期", "代号", "用量", "钟点", "备注"] if chinese else ["Associated date", "Alias", "Amount", "Clock time", "Note"]), hide_index=True)
