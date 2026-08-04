import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine

# ============================================
# 1. Récupération des données réelles depuis PostgreSQL
# ============================================
query = """
SELECT
    hl.habit_id,
    hl.user_id,
    hl.log_date,
    hl.completed,
    h.streak_count,
    EXTRACT(DOW FROM hl.log_date) AS day_of_week
FROM habit_logs hl
JOIN habits h ON h.id = hl.habit_id
ORDER BY hl.user_id, hl.log_date
"""
data = pd.read_sql(query, engine)

print(f"Nombre de logs récupérés : {len(data)}")

if len(data) < 30:
    print("⚠️  Pas assez de données réelles (minimum ~30 logs recommandé).")
    sys.exit(0)

# ============================================
# 2. Feature engineering
# ============================================
data["is_weekend"] = (data["day_of_week"].isin([0, 6])).astype(int)

data["missed_last_7_days"] = data.groupby("user_id")["completed"].transform(
    lambda x: (~x.astype(bool)).rolling(7, min_periods=1).sum()
)

data["completion_rate_14d"] = data.groupby("user_id")["completed"].transform(
    lambda x: x.astype(int).rolling(14, min_periods=1).mean()
)
data["completion_rate_30d"] = data.groupby("user_id")["completed"].transform(
    lambda x: x.astype(int).rolling(30, min_periods=1).mean()
)

data["completed_yesterday"] = data.groupby("user_id")["completed"].shift(1).fillna(0).astype(int)

data["user_id_encoded"] = data["user_id"].astype("category").cat.codes

X = data[[
    "streak_count", "day_of_week", "is_weekend",
    "missed_last_7_days", "completion_rate_14d", "completion_rate_30d",
    "completed_yesterday", "user_id_encoded",
]]
y = data["completed"].astype(int)

# ============================================
# 3. Entraînement
# ============================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_leaf=5,
    class_weight="balanced",
    random_state=42,
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nImportance des features:")
print(importances)

# ============================================
# 4. Sauvegarde
# ============================================
# Sauvegarde du modèle + mapping des user_id (nécessaire pour encoder de nouveaux users)
user_mapping = dict(enumerate(data["user_id"].astype("category").cat.categories))
user_mapping_reverse = {v: k for k, v in user_mapping.items()}

bundle = {
    "model": model,
    "user_mapping": user_mapping_reverse,
    "features": list(X.columns),
}
joblib.dump(bundle, "ml/habit_predictor.pkl")
print("\nModèle + mapping sauvegardés -> ml/habit_predictor.pkl")