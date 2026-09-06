import joblib
import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Interactive 3D Surfaces", page_icon="📊", layout="wide")

st.title("📊 3D Polymer Interaction Maps")
st.markdown("Explore how varying plasticizers and solvent ratios continuously affect bioplastic strength.")

model = joblib.load("models/bioplastic_rf_v1.pkl")

g_range = np.linspace(5, 40, 20)
w_range = np.linspace(10, 50, 20)
G, W = np.meshgrid(g_range, w_range)

Z = np.zeros(G.shape)
for i in range(G.shape[0]):
    for j in range(G.shape[1]):
        X_test = np.array([[G[i, j], W[i, j], 2.0, 1.0]])
        Z[i, j] = model.predict(X_test)[0][0]

fig = go.Figure(data=[go.Surface(z=Z, x=G, y=W, colorscale='Viridis')])
fig.update_layout(
    title='Tensile Strength (MPa) across Glycerin vs Water Ratios',
    scene=dict(
        xaxis_title='Glycerin (g)',
        yaxis_title='Water (g)',
        zaxis_title='Tensile Strength (MPa)'
    ),
    height=600
)

st.plotly_chart(fig, use_container_width=True)
