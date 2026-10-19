import sqlite3, pandas as pd
con = sqlite3.connect("data/campus.db")
pd.set_option("display.width", 250, "display.max_colwidth", 40, "display.max_rows", 100)
print(pd.read_sql("SELECT file, issue_type, rows_affected, before_count, after_count FROM cleaning_log", con))
print(pd.read_sql("SELECT mentor_id, COUNT(*) n FROM students_unified GROUP BY mentor_id", con))