from collections import deque  # Only stores limited number of recent values
from typing import Callable, List, Dict, Sequence  # Defines data types
import time  

import dash  # Creates the dashboard
from dash import dcc, html, Output, Input  # Dashboard components
from dash import Patch  # Update parts of the graph
import plotly.graph_objects as go  # Create the graph


def create_smooth_stream_app( # Defines dashboard settings
    get_new_samples: Callable[[], List[Dict]],
    channels: Sequence[str] = ("x", "y", "z"),
    window_size: int = 200,
    update_interval_ms: int = 100,
    title: str = "Live Data Stream",
    y_label: str = "Value",
    colors: Sequence[str] = ("#EF553B", "#00CC96", "#636EFA"),
) -> dash.Dash:

    channel_data: Dict[str, deque] = {ch: deque(maxlen=window_size) for ch in channels}  # Stores recent values for each channel
    time_data: deque = deque(maxlen=window_size)  # Stores recent time values
    start_time = time.time()  # Records the starting time

    app = dash.Dash(__name__)  # Creates the Dash app

    fig = go.Figure()  # Creates an empty graph
    for i, ch in enumerate(channels):  # Creates a line for each channel
        fig.add_trace(
            go.Scattergl(
                x=[],
                y=[],
                mode="lines",
                name=ch,
                line=dict(color=colors[i % len(colors)], width=2),
            )
        )
    fig.update_layout(
        title=title,  # Sets the graph title
        xaxis_title="Time (s)",  # Sets the X-axis label
        yaxis_title=y_label,  # Sets the Y-axis label
        uirevision="keep",  # Keeps the graph view when it updates
        margin=dict(l=50, r=20, t=50, b=40),
        template="plotly_white",
    )

    app.layout = html.Div(
        [
            dcc.Graph(id="live-graph", figure=fig, animate=False),  # Displays the live graph
            dcc.Interval(id="tick", interval=update_interval_ms, n_intervals=0),  # Controls how often the graph updates
        ]
    )

    @app.callback(
        Output("live-graph", "figure"),
        Input("tick", "n_intervals"),
        prevent_initial_call=True,
    )
    def _update(_n):
        new_samples = get_new_samples()  # Gets any new readings
        if not new_samples:
            raise dash.exceptions.PreventUpdate  # Does not update if there is no new data

        for s in new_samples:
            time_data.append(s.get("t", time.time() - start_time))  # Adds the time value
            for ch in channels:
                channel_data[ch].append(s.get(ch))  # Adds each channel value

        
        patched = Patch()  # Prepares the graph update
        for i, ch in enumerate(channels):
            patched["data"][i]["x"] = list(time_data)  # Updates the time values
            patched["data"][i]["y"] = list(channel_data[ch])  # Updates the channel values
        return patched  # Sends the updated data to the graph

    return app  # Returns the completed Dash app
