from uuid import uuid4
from psycopg.types.json import Jsonb
from foundation import connect


def one(query, params=()):
    with connect() as db:
        return db.execute(query, params).fetchone()


def many(query, params):
    with connect() as db:
        return db.execute(query, params).fetchall()


def register(email, digest):
    return one(
        "INSERT INTO users VALUES (%s,%s,%s) RETURNING id,email",
        (str(uuid4()), email, digest),
    )


def user(email):
    return one("SELECT * FROM users WHERE email=%s", (email,))


def save_profile(profile):
    body = Jsonb(profile.model_dump())
    return one(
        """INSERT INTO profiles VALUES (%s,%s,1) ON CONFLICT(user_id) DO UPDATE SET
        version=profiles.version+(profiles.profile<>excluded.profile)::int, profile=excluded.profile
        RETURNING profile,version""",
        (profile.user_id, body),
    )


def profile(uid):
    return one("SELECT profile,version FROM profiles WHERE user_id=%s", (uid,))


def add_version(uid, body, idea_id=None):
    with connect() as db:
        if idea_id is None:
            idea_id = str(uuid4())
            db.execute("INSERT INTO ideas(id,user_id) VALUES(%s,%s)", (idea_id, uid))
        if not db.execute(
            "SELECT id FROM ideas WHERE id=%s AND user_id=%s FOR UPDATE", (idea_id, uid)
        ).fetchone():
            return None
        return db.execute(
            """INSERT INTO idea_versions SELECT %s,coalesce(max(version),0)+1,%s
            FROM idea_versions WHERE idea_id=%s RETURNING *""",
            (idea_id, Jsonb(body), idea_id),
        ).fetchone()


def history(uid, idea_id=None):
    return many(
        """SELECT v.*, coalesce((SELECT jsonb_agg(w.body ORDER BY w.run_id)
        FROM verdicts w WHERE (w.idea_id,w.version)=(v.idea_id,v.version)), '[]') AS verdicts
        FROM idea_versions v JOIN ideas i ON i.id=v.idea_id WHERE i.user_id=%s
        AND (%s::text IS NULL OR i.id=%s) ORDER BY i.created_at DESC,v.version DESC""",
        (uid, idea_id, idea_id),
    )


def save_run(run_id, body):
    return one(
        """INSERT INTO runs(run_id,user_id,idea_id,mode,state,state_json,budget_json)
        SELECT %s,%s,%s,%s,%s,%s,%s WHERE %s::text IS NULL OR EXISTS
        (SELECT 1 FROM ideas WHERE id=%s AND user_id=%s)
        ON CONFLICT(run_id) DO UPDATE SET state=excluded.state,state_json=excluded.state_json,
        budget_json=excluded.budget_json,updated_at=now() WHERE runs.user_id=excluded.user_id
        AND runs.idea_id IS NOT DISTINCT FROM excluded.idea_id AND runs.mode=excluded.mode RETURNING *""",
        (
            run_id,
            body.user_id,
            body.idea_id,
            body.mode,
            body.state,
            Jsonb(body.state_json),
            Jsonb(body.budget_json),
            body.idea_id,
            body.idea_id,
            body.user_id,
        ),
    )


def verdict(v):
    with connect() as db:
        row = db.execute(
            """INSERT INTO verdicts SELECT run_id,idea_id,%s,%s,%s,%s,%s FROM runs
            WHERE run_id=%s AND idea_id=%s ON CONFLICT(run_id) DO UPDATE SET body=excluded.body,
            version=excluded.version,versions=excluded.versions,gates=excluded.gates,
            missing_evidence=excluded.missing_evidence RETURNING run_id""",
            (
                v.version,
                Jsonb(v.model_dump()),
                Jsonb(v.versions.model_dump()),
                Jsonb(v.model_dump()["gates"]),
                Jsonb(v.missing_evidence),
                v.run_id,
                v.idea_id,
            ),
        ).fetchone()
        if row:
            for score in v.scores:
                db.execute(
                    """INSERT INTO dimension_scores VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(run_id,dimension) DO UPDATE SET abstained=excluded.abstained,
                    features=excluded.features,rubric_version=excluded.rubric_version,model=excluded.model,body=excluded.body""",
                    (
                        v.run_id,
                        score.dimension,
                        score.abstained,
                        Jsonb(score.features),
                        score.rubric_version,
                        score.model,
                        Jsonb(score.model_dump()),
                    ),
                )
        return row


def approval(run_id, reason):
    return one(
        "INSERT INTO approvals(id,run_id,reason) VALUES (%s,%s,%s) RETURNING *",
        (str(uuid4()), run_id, reason),
    )


def decide(aid, decision):
    return one(
        "UPDATE approvals SET decision=%s WHERE id=%s AND (decision IS NULL OR decision=%s) RETURNING *",
        (decision, aid, decision),
    )


def get_run(run_id):
    return one("SELECT * FROM runs WHERE run_id=%s", (run_id,))


def get_approvals(run_id):
    return many("SELECT * FROM approvals WHERE run_id=%s ORDER BY id", (run_id,))


def get_verdict(run_id):
    row = one("SELECT body FROM verdicts WHERE run_id=%s", (run_id,))
    return row["body"] if row else None
