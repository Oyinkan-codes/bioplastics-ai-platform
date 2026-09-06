import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

def train_and_save_model():
    np.random.seed(42)
    n_samples = 600

    cassava_waste = np.random.uniform(20, 50, n_samples)
    brewery_spent_grain = np.random.uniform(10, 30, n_samples)
    palm_kernel_ash = np.random.uniform(2, 15, n_samples)
    glycerin_binder = np.random.uniform(10, 25, n_samples)
    chitosan = np.random.uniform(2, 10, n_samples)

    tensile_strength = (
        0.7 * cassava_waste + 1.2 * brewery_spent_grain + 1.5 * palm_kernel_ash - 0.4 * glycerin_binder + np.random.normal(0, 2, n_samples)
    )
    elongation = (
        2.2 * glycerin_binder - 0.4 * cassava_waste - 0.3 * palm_kernel_ash + np.random.normal(0, 3, n_samples)
    )
    hdt = (
        50 + 1.8 * palm_kernel_ash + 0.9 * brewery_spent_grain - 0.5 * glycerin_binder + np.random.normal(0, 2, n_samples)
    )
    marine_degradability = (
        180 - 1.8 * palm_kernel_ash - 1.2 * chitosan + 0.9 * glycerin_binder + np.random.normal(0, 5, n_samples)
    )
    wvtr = (
        140 - 2.5 * palm_kernel_ash - 1.9 * chitosan + 1.1 * glycerin_binder + np.random.normal(0, 4, n_samples)
    )

    X = pd.DataFrame({
        "cassava_waste": cassava_waste,
        "brewery_spent_grain": brewery_spent_grain,
        "palm_kernel_ash": palm_kernel_ash,
        "glycerin_binder": glycerin_binder,
        "chitosan": chitosan
    })

    Y = pd.DataFrame({
        "tensile_strength": tensile_strength,
        "elongation": elongation,
        "hdt": hdt,
        "marine_degradability": marine_degradability,
        "wvtr": wvtr
    })

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, Y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/bioplastic_rf_v1.pkl")
    print("✅ Model updated with Novel Feedstocks & Performance Metrics!")

if __name__ == "__main__":
    train_and_save_model()
