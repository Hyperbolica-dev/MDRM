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
    assert len(figure.data) == 8
    assert figure.layout.scene.xaxis.title.text == "P phase (h)"
    assert figure.layout.scene.yaxis.title.text == "D sleep debt (h)"
    assert figure.layout.scene.zaxis.title.text == "Time from latest (days)"
    assert figure.layout.scene.camera.eye.x > 0
    assert figure.layout.scene.camera.eye.y > 0
    assert figure.layout.scene.camera.projection.type == "orthographic"
    assert build_phase_space_3d_figure(frame(), view="pd").layout.scene.camera.eye.x == 0


def test_3d_figure_fades_older_time_buckets():
    figure = build_phase_space_3d_figure(frame())
    trajectory_traces = [trace for trace in figure.data if trace.name and trace.name.startswith("Age bucket")]
    assert [trace.marker.opacity for trace in trajectory_traces] == sorted(trace.marker.opacity for trace in trajectory_traces)
    assert trajectory_traces[0].marker.opacity < trajectory_traces[-1].marker.opacity
    assert max(trajectory_traces[0].z) < min(trajectory_traces[-1].z)


def test_3d_line_spans_color_buckets_but_not_missing_dates():
    points = frame()
    figure = build_phase_space_3d_figure(points)
    assert list(figure.data[0].x) == points["P"].tolist()
    points.loc[1, "P"] = None
    figure = build_phase_space_3d_figure(points, view="phase_time", chinese=True)
    assert pd.isna(figure.data[0].x[1])
    assert figure.layout.scene.camera.eye.y == 2.5
    latest = next(trace for trace in figure.data if trace.name == "最新记录")
    assert latest.text[0] == "2026-08-04"
