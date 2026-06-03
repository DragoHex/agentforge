#!/usr/bin/env python3
"""
Generate charts and graphs using Plotly and Seaborn for article visualizations.

Usage:
    python3 .pi/skills/create-visualization/generate_graph.py --type bar --title "Title" \
        --data '[{"label":"A","value":10}]' --output output/chart.png

    python3 .pi/skills/create-visualization/generate_graph.py --type grouped_bar --title "Comparison" \
        --data-file data.json --output output/chart.png

Chart types: bar, grouped_bar, line, scatter, pie, heatmap, histogram, box

Data formats:
    bar/line/pie/histogram/box:  [{"label": "A", "value": 10}, ...]
    grouped_bar:                 [{"label": "X", "Series1": 10, "Series2": 20}, ...]
    scatter:                     [{"x": 1.0, "y": 2.0, "label": "P"}, ...]
    heatmap:                     [{"x": "Col", "y": "Row", "value": 0.9}, ...]
"""

import sys
import os
import json
import argparse


def load_data(args):
    if args.data_file:
        with open(args.data_file) as f:
            return json.load(f)
    if args.data:
        return json.loads(args.data)
    print("Error: provide --data or --data-file", file=sys.stderr)
    sys.exit(1)


def create_bar_chart(data, title, output_path):
    import plotly.express as px
    df = _to_frame(data)
    fig = px.bar(df, x="label", y="value", title=title, text="value")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(template="plotly_white", font=dict(size=14), uniformtext_minsize=10)
    fig.write_image(output_path, scale=2)
    print(f"Bar chart saved to {output_path}")


def create_grouped_bar_chart(data, title, output_path):
    """Multi-series bar chart. Data: [{"label": "X", "Series1": v, "Series2": v}, ...]"""
    import plotly.graph_objects as go
    import pandas as pd

    df = pd.DataFrame(data)
    labels = df["label"].tolist()
    series_cols = [c for c in df.columns if c != "label"]

    fig = go.Figure()
    for col in series_cols:
        fig.add_trace(go.Bar(name=col, x=labels, y=df[col].tolist(), text=df[col].tolist(),
                             texttemplate="%{text:.1f}", textposition="outside"))
    fig.update_layout(
        title=title, barmode="group", template="plotly_white",
        font=dict(size=14), legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.write_image(output_path, scale=2)
    print(f"Grouped bar chart saved to {output_path}")


def create_line_chart(data, title, output_path):
    import plotly.express as px
    df = _to_frame(data)
    fig = px.line(df, x="label", y="value", title=title, markers=True)
    fig.update_layout(template="plotly_white", font=dict(size=14))
    fig.write_image(output_path, scale=2)
    print(f"Line chart saved to {output_path}")


def create_scatter_chart(data, title, output_path):
    """Scatter plot. Data: [{"x": float, "y": float, "label": str}, ...]"""
    import plotly.express as px
    import pandas as pd

    df = pd.DataFrame(data)
    if "x" not in df.columns or "y" not in df.columns:
        print("Error: scatter data must have 'x' and 'y' fields", file=sys.stderr)
        sys.exit(1)
    hover = df["label"] if "label" in df.columns else None
    fig = px.scatter(df, x="x", y="y", title=title, hover_name=hover, size_max=15)
    if hover is not None:
        fig.update_traces(text=df["label"], textposition="top center", mode="markers+text")
    fig.update_layout(template="plotly_white", font=dict(size=14))
    fig.write_image(output_path, scale=2)
    print(f"Scatter plot saved to {output_path}")


def create_pie_chart(data, title, output_path):
    import plotly.express as px
    df = _to_frame(data)
    fig = px.pie(df, names="label", values="value", title=title)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white", font=dict(size=14))
    fig.write_image(output_path, scale=2)
    print(f"Pie chart saved to {output_path}")


def create_heatmap(data, title, output_path):
    import seaborn as sns
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    df = pd.DataFrame(data)
    pivot = df.pivot_table(index="y", columns="x", values="value", aggfunc="mean")
    plt.figure(figsize=(max(8, len(pivot.columns) * 1.2), max(6, len(pivot) * 0.8)))
    sns.heatmap(pivot, annot=True, cmap="YlOrRd", fmt=".2f", linewidths=0.5)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Heatmap saved to {output_path}")


def create_histogram(data, title, output_path):
    import seaborn as sns
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = [d.get("value", 0) for d in data] if isinstance(data[0], dict) else data
    plt.figure(figsize=(10, 6))
    sns.histplot(values, bins=15, kde=True)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Histogram saved to {output_path}")


def create_box_plot(data, title, output_path):
    import plotly.express as px
    df = _to_frame(data)
    fig = px.box(df, x="label", y="value", title=title)
    fig.update_layout(template="plotly_white", font=dict(size=14))
    fig.write_image(output_path, scale=2)
    print(f"Box plot saved to {output_path}")


def _to_frame(data):
    import pandas as pd
    if not data:
        return pd.DataFrame({"label": [], "value": []})
    if isinstance(data[0], dict) and "label" in data[0] and "value" in data[0]:
        return pd.DataFrame(data)
    if isinstance(data[0], dict):
        return pd.DataFrame(data)
    return pd.DataFrame({"label": [str(i) for i in range(len(data))], "value": data})


def main():
    parser = argparse.ArgumentParser(description="Generate charts and graphs")
    parser.add_argument("--type", required=True,
                        choices=["bar", "grouped_bar", "line", "scatter", "pie",
                                 "heatmap", "histogram", "box"],
                        help="Chart type")
    parser.add_argument("--title", default="Chart", help="Chart title")
    parser.add_argument("--data", help="JSON data array (inline)")
    parser.add_argument("--data-file", help="Path to JSON file containing data array")
    parser.add_argument("--output", "-o", required=True, help="Output image path (.png)")
    args = parser.parse_args()

    if not args.data and not args.data_file:
        parser.error("Provide either --data or --data-file")

    data = load_data(args)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    chart_fns = {
        "bar": create_bar_chart,
        "grouped_bar": create_grouped_bar_chart,
        "line": create_line_chart,
        "scatter": create_scatter_chart,
        "pie": create_pie_chart,
        "heatmap": create_heatmap,
        "histogram": create_histogram,
        "box": create_box_plot,
    }

    try:
        chart_fns[args.type](data, args.title, args.output)
    except ImportError as e:
        pkg = str(e).split("'")[1] if "'" in str(e) else "required library"
        print(f"Error: missing '{pkg}'. Run: pip install {pkg.lower()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating chart: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
