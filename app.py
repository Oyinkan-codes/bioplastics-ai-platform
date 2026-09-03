import streamlit as st
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

st.set_page_config(page_title="Bioplastics AI Platform", layout="wide")

Base = declarative_base()

class Formulation(Base):
    __tablename__ = 'formulations'
    id = Column(Integer, primary_key=True)
    batch_code = Column(String)
    agar_percent = Column(Float)
    starch_percent = Column(Float)
    glycerin_percent = Column(Float)
    sorbitol_percent = Column(Float)
    water_percent = Column(Float)

class PropertyTest(Base):
    __tablename__ = 'property_tests'
    id = Column(Integer, primary_key=True)
    formulation_id = Column(Integer, ForeignKey('formulations.id'))
    tensile_strength_mpa = Column(Float)
    elastic_modulus_gpa = Column(Float)
    water_absorption_percent = Column(Float)

engine = create_engine('sqlite:///bioplastics.db')
Session = sessionmaker(bind=engine)

@st.cache_resource
def load_and_train():
    session = Session()
    query = session.query(Formulation, PropertyTest).join(
        PropertyTest, Formulation.id == PropertyTest.formulation_id
    )
    
    data = []
    for form, test in query.all():
        data.append({
            'agar_percent': form.agar_percent or 0.0,
            'starch_percent': getattr(form, 'starch_percent', 0.0) or 0.0,
            'glycerin_percent': form.glycerin_percent or 0.0,
            'sorbitol_percent': getattr(form, 'sorbitol_percent', 0.0) or 0.0,
            'tensile_strength': test.tensile_strength_mpa,
            'elastic_modulus': test.elastic_modulus_gpa,
            'water_absorption': test.water_absorption_percent
        })
    session.close()
    
    df = pd.DataFrame(data)
    
    X = df[['tensile_strength', 'elastic_modulus', 'water_absorption']].values
    y = df[['agar_percent', 'starch_percent', 'glycerin_percent', 'sorbitol_percent']].values
    
    x_scaler = MinMaxScaler()
    y_scaler = MinMaxScaler()
    
    X_scaled = x_scaler.fit_transform(X)
    y_scaled = y_scaler.fit_transform(y)
    
    # Lightweight Multi-Layer Perceptron (Neural Network)
    model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
    model.fit(X_scaled, y_scaled)
    
    return model, x_scaler, y_scaler

model, x_scaler, y_scaler = load_and_train()

st.title("🌱 Bioplastics AI Formulation Platform")
st.write("Adjust target properties to generate optimal chemical formulation ratios.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Target Mechanical Properties")
    tensile = st.slider("Tensile Strength (MPa)", 10.0, 50.0, 30.0, 0.5)
    elastic = st.slider("Elastic Modulus (GPa)", 0.5, 3.5, 2.0, 0.1)
    water_abs = st.slider("Water Absorption (%)", 20.0, 60.0, 40.0, 1.0)

with col2:
    st.subheader("AI Recommended Recipe")
    X_in = x_scaler.transform([[tensile, elastic, water_abs]])
    pred_scaled = model.predict(X_in)
    pred_actual = y_scaler.inverse_transform(pred_scaled)[0]
    
    agar_pct = max(0.0, float(pred_actual[0]))
    starch_pct = max(0.0, float(pred_actual[1]))
    gly_pct = max(0.0, float(pred_actual[2]))
    sorb_pct = max(0.0, float(pred_actual[3]))
    solvent_pct = max(0.0, 100.0 - (agar_pct + starch_pct + gly_pct + sorb_pct))
    
    st.metric("Recommended Agar (%)", f"{agar_pct:.2f}%")
    st.metric("Recommended Starch (%)", f"{starch_pct:.2f}%")
    st.metric("Recommended Glycerin (%)", f"{gly_pct:.2f}%")
    st.metric("Recommended Sorbitol (%)", f"{sorb_pct:.2f}%")
    st.metric("Water / Solvent Balance (%)", f"{solvent_pct:.2f}%")
