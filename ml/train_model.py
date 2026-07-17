import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import joblib

# =====================================================
# STEP 1: Load dataset
# =====================================================

# NOTE: this must match env.py's CoverageExport output path exactly --
# "results/coverage_log.csv", not "axi_coverage_log.csv".
#
# keep_default_na=False is REQUIRED here: pandas' default read_csv
# behavior silently converts the literal string "NA" (which our
# data_type column legitimately uses for READ transactions and
# invalid-address WRITEs) into an actual float NaN on read. Without
# this flag, every "NA" row becomes an unmapped NaN after the STEP 3
# encoding below, which then poisons KMeans in cluster_tests.py
# ("Input X contains NaN"). This is a pandas CSV-reading default, not
# a flaw in the coverage CSV itself.

df = pd.read_csv("../results/coverage_log.csv", keep_default_na=False)

print("Dataset loaded:")
print(df.head())

# =====================================================
# STEP 2: Select columns
# =====================================================

df = df[
    [
        "txn_type",
        "addr_category",
        "data_type",
        "gain_label"
    ]
]

# =====================================================
# STEP 3: Encoding
# =====================================================

txn_map = {
    "WRITE": 0,
    "READ": 1
}

addr_map = {
    "REG0": 0,
    "REG1": 1,
    "REG2": 2,
    "REG3": 3,
    "INVALID": 4
}

data_map = {
    "ZERO": 0,
    "SMALL": 1,
    "LARGE": 2,
    "NA": 3
}

df["txn_type"] = df["txn_type"].map(txn_map)
df["addr_category"] = df["addr_category"].map(addr_map)
df["data_type"] = df["data_type"].map(data_map)

# =====================================================
# STEP 4: Numeric types
# =====================================================

df["gain_label"] = df["gain_label"].astype(int)

# =====================================================
# STEP 5: Features and target
# =====================================================

X = df[
    [
        "txn_type",
        "addr_category",
        "data_type"
    ]
]

y = df["gain_label"]

# =====================================================
# STEP 6: Train model
# =====================================================

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

print("Model trained!")

# =====================================================
# STEP 7: Predict coverage gain
# =====================================================

df["predicted_gain"] = model.predict_proba(X)[:, 1]

# =====================================================
# STEP 8: Sort by priority
# =====================================================

df_sorted = df.sort_values(
    by="predicted_gain",
    ascending=False
)

print("Top prioritized testcases:")
print(df_sorted.head())

# =====================================================
# STEP 9: Save prioritized list
# =====================================================

df_sorted.to_csv(
    "prioritized_tests.csv",
    index=False
)

print("Saved prioritized_tests.csv")

# =====================================================
# STEP 10: Save model
# =====================================================

joblib.dump(
    model,
    "model.pkl"
)

print("Model saved as model.pkl")

# =====================================================
# STEP 11: Plot priority curve
# =====================================================

plt.plot(df_sorted["predicted_gain"].values)

plt.title("AXI Testcase Priority Curve")
plt.xlabel("Testcases")
plt.ylabel("Predicted Coverage Gain")

plt.savefig("priority_plot.png")

print("Plot saved as priority_plot.png")