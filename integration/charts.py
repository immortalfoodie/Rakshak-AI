"""Plotly chart builders for the dashboard."""
import plotly.graph_objects as go


CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#E0E0E0"),
    margin=dict(l=40, r=20, t=40, b=40),
    height=280,
)


def _make_line(data: list[dict], title: str, y_label: str, color: str) -> go.Figure:
    days = [p["day"] for p in data]
    vals = [p["value"] for p in data]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=vals, mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=7, color=color),
        fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
    ))
    fig.update_layout(**CHART_LAYOUT, title=title,
                       xaxis_title="Day", yaxis_title=y_label)
    return fig


def brent_chart(projections: dict) -> go.Figure:
    return _make_line(projections["brent_price_usd"],
                      "Brent Crude Price Projection", "USD/bbl", "#FF6B6B")


def inr_chart(projections: dict) -> go.Figure:
    return _make_line(projections["inr_usd_rate"],
                      "INR/USD Exchange Rate", "₹/USD", "#4ECDC4")


def fuel_chart(projections: dict) -> go.Figure:
    return _make_line(projections["domestic_fuel_price_inr_per_liter"],
                      "Domestic Fuel Price", "₹/litre", "#FFEAA7")


def state_bar(projections: dict) -> go.Figure:
    states = [s["state"] for s in projections["state_impact"]]
    stress = [s["stress_index"] for s in projections["state_impact"]]
    colors = ["#FF4444" if v > 0.7 else "#FFA726" if v > 0.5 else "#66BB6A" for v in stress]
    fig = go.Figure(go.Bar(x=states, y=stress, marker_color=colors))
    fig.update_layout(**CHART_LAYOUT, title="State-wise Stress Index",
                       yaxis_title="Stress Index (0-1)")
    return fig
