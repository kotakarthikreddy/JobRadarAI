import sqlite3

c = sqlite3.connect("data/jobradar.db")
c.row_factory = sqlite3.Row
total = c.execute("select count(*) from job_tracker").fetchone()[0]
h1b = c.execute(
    "select count(*) from job_tracker where h1b_sponsor like '%Yes%' or h1b_sponsor like '%Verified%'"
).fetchone()[0]
score60 = c.execute("select count(*) from job_tracker where match_score>=60").fetchone()[0]
ml = c.execute(
    """select count(*) from job_tracker where
    lower(job_title) like '%ml%' or lower(job_title) like '%machine learning%'
    or lower(job_title) like '%ai engineer%' or lower(job_title) like '%data scientist%'
    or lower(job_title) like '%llm%' or lower(job_title) like '%nlp%'"""
).fetchone()[0]
print(f"total={total} h1b={h1b} score60={score60} ml={ml}")
for r in c.execute(
    "select job_title, company, match_score, h1b_sponsor from job_tracker order by detected_at desc limit 10"
):
    print(dict(r))
