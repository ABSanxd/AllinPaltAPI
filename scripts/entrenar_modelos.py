import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, classification_report
import numpy as np
import os

# Determinar la ruta del archivo CSV de manera robusta
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(base_dir, "data", "predicciones_entrenamiento.csv")

print(f"Cargando dataset desde: {csv_path}")

# Load dataset
df = pd.read_csv(csv_path)

X = df[["temperatura_ambiente", "madurez_promedio", "dias_cosecha"]]
y_vida = df["vida_util_estimada"]
y_riesgo = df["riesgo_deterioro"]
y_prioridad = df["prioridad_venta"]

# Split data
X_train, X_test, y_vida_train, y_vida_test = train_test_split(X, y_vida, test_size=0.2, random_state=42)
_, _, y_riesgo_train, y_riesgo_test = train_test_split(X, y_riesgo, test_size=0.2, random_state=42)
_, _, y_prioridad_train, y_prioridad_test = train_test_split(X, y_prioridad, test_size=0.2, random_state=42)

# Regressor for life
model_vida = RandomForestRegressor(n_estimators=100, random_state=42)
model_vida.fit(X_train, y_vida_train)
y_vida_pred = model_vida.predict(X_test)

mae = mean_absolute_error(y_vida_test, y_vida_pred)
rmse = np.sqrt(mean_squared_error(y_vida_test, y_vida_pred))
r2 = r2_score(y_vida_test, y_vida_pred)

print("\n--- REGRESION VIDA UTIL ---")
print(f"MAE: {mae:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"R2: {r2:.4f}")

# Classifier for risk
model_riesgo = RandomForestClassifier(n_estimators=100, random_state=42)
model_riesgo.fit(X_train, y_riesgo_train)
y_riesgo_pred = model_riesgo.predict(X_test)
acc_riesgo = accuracy_score(y_riesgo_test, y_riesgo_pred)

print("\n--- CLASIFICACION RIESGO ---")
print(f"Accuracy: {acc_riesgo:.4f}")
print(classification_report(y_riesgo_test, y_riesgo_pred))

# Classifier for priority
model_prioridad = RandomForestClassifier(n_estimators=100, random_state=42)
model_prioridad.fit(X_train, y_prioridad_train)
y_prioridad_pred = model_prioridad.predict(X_test)
acc_prioridad = accuracy_score(y_prioridad_test, y_prioridad_pred)

print("\n--- CLASIFICACION PRIORIDAD ---")
print(f"Accuracy: {acc_prioridad:.4f}")
print(classification_report(y_prioridad_test, y_prioridad_pred))
