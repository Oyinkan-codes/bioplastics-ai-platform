import os
import joblib
import numpy as np
import streamlit as st
import plotly.graph_objects as go

MODEL_PATH = "models/bioplastic_rf_v1.pkl"

@st.cache_resource
def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

model = load_model()

st.header("3. Polymer Interaction Surfaces")

if model:
    g_range = np.linspace(5, 40, 30)
    w_range = np.linspace(10, 50, 30)
    G, W = np.meshgrid(g_range, w_range)

    grid_inputs = np.column_stack([G.ravel(), W.ravel(), np.full(G.size, 2.0), np.full(G.size, 1.0)])
    grid_preds = model.predict(grid_inputs)
    Z_tensile = grid_preds[:, 0].reshape(G.shape)

    fig = go.Figure(data=[go.Surface(z=Z_tensile, x=G, y=W, colorscale='Viridis')])
    fig.update_layout(
        title="3D Tensile Strength Surface (MPa)",
        scene=dict(xaxis_title="Glycerin (%)", yaxis_title="Water Content (%)", zaxis_title="Tensile (MPa)")
    )
    st.plotly_chart(fig, use_container_width=True)
