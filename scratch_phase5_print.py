import sqlite3
import pandas as pd
from core.score import get_segments_analytics, score_all

print("Re-scoring so stored cluster personas match centroid labels...")
score_all(verbose=False)

conn = sqlite3.connect("data/campus.db")
df = pd.read_sql("SELECT * FROM students_scored", conn)
conn.close()

analytics = get_segments_analytics(df)

print("\n=== INSIGHT TITLE ===")
print(analytics["insight_title"])

print("\n=== RAW RULE SEGMENT TABLE ===")
print(analytics["rule_table"].to_string(index=False))

print("\n=== K-MEANS CENTROIDS ===")
print(analytics["centroids"].to_string(index=False))

print("\n=== CLUSTER TABLE ===")
print(analytics["cluster_table"].to_string(index=False))

print("\n=== CROSS-TAB PERSONA vs RULE SEGMENT ===")
print(analytics["cross_tab"].to_string())

print("\n=== stored cluster_label value counts ===")
print(df["cluster_label"].value_counts().to_string())
print("\nany 'Cluster ' prefix?", df["cluster_label"].astype(str).str.contains(r"Cluster\s+\d").any())
