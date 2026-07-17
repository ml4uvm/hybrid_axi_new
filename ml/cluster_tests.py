import pandas as pd
from sklearn.cluster import KMeans

# ==========================================================
# Load prioritized testcases
# ==========================================================

# keep_default_na=False prevents pandas from converting the
# literal string "NA" into NaN.

df = pd.read_csv(
    "prioritized_tests.csv",
    keep_default_na=False,
)

print("Original size:", len(df))

# ==========================================================
# Features used for clustering
# ==========================================================

# Use only encoded stimulus fields plus predicted_gain.
# This matches the ALU/FIFO methodology.

X = df[
    [
        "txn_type",
        "addr_category",
        "data_type",
        "predicted_gain",
    ]
]

# ==========================================================
# KMeans clustering
# ==========================================================

# Number of clusters = TOTAL_BINS (18)

k = min(18, len(df))

kmeans = KMeans(
    n_clusters=k,
    random_state=42,
)

df["cluster"] = kmeans.fit_predict(X)

# ==========================================================
# Pick highest-priority testcase from each cluster
# ==========================================================

best_tests = df.loc[
    df.groupby("cluster")["predicted_gain"].idxmax()
]

# ==========================================================
# Sort by predicted gain
# ==========================================================

best_tests = best_tests.sort_values(
    by="predicted_gain",
    ascending=False,
)

# ==========================================================
# Save clustered testcases
# ==========================================================

best_tests[
    [
        "txn_type",
        "addr_category",
        "data_type",
        "predicted_gain",
        "cluster",
    ]
].to_csv(
    "clustered_tests.csv",
    index=False,
)

print("Reduced size:", len(best_tests))
print(best_tests.head())