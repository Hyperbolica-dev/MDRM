import pandas as pd

from ui.phase_space_3d import build_phase_space_3d_figure, prepare_phase_space_3d_frame


def frame():
    return pd.DataFrame([
        {
            "rhythm_day": day,
            "P": phase,
            "D": debt,
            "H": 0.5,
            "disturbance": disturbance,
            "recovery_days": None,
        }
        for day, phase, debt, disturbance in [
            ("2026-08-01", 2.0, 6.0, 0),
            ("2026-08-02", 1.5, 5.0, 1),
            ("2026-08-03", 1.0, 4.0, 0),
            ("2026-08-04", 0.5, 3.0, 0),
        ]
    ])


def test_3d_frame_uses_relative_time_and_time_buckets():
    prepared = prepare_phase_space_3d_frame(frame())
    assert prepared["time_offset_days"].tolist() == [-3.0, -2.0, -1.0, 0.0]
    assert prepared["time_bucket"].between(0, 3).all()


def test_3d_figure_has_p_d_time_axes_and_default_projection_camera():
    figure = build_phase_space_3d_figure(frame())
    assert figure is not None
    assert len(figure.data) == 6
    assert figure.layout.scene.xaxis.title.text == "P phase (h)"
    assert figure.layout.scene.yaxis.title.text == "D sleep debt (h)"
    assert figure.layout.scene.zaxis.title.text == "Time from latest (days)"
    assert figure.layout.scene.camera.eye.x == 0.0
    assert figure.layout.scene.camera.eye.y == 0.0


def test_3d_figure_fades_older_time_buckets():
    figure = build_phase_space_3d_figure(frame())
    trajectory_traces = [trace for trace in figure.data if trace.mode == "lines+markers"]
    assert [trace.opacity for trace in trajectory_traces] == sorted(trace.opacity for trace in trajectory_traces)
    assert trajectory_traces[0].opacity < trajectory_traces[-1].opacity
