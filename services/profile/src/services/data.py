from ..repositories import store


def profile(uid, body=None):
    row = store.save_profile(body) if body else store.profile(uid)
    if row:
        return {**row["profile"], "version": row["version"]}


def compare(uid, a, b):
    left, right = store.history(uid, a), store.history(uid, b)
    if left and right:
        return {"a": left[0], "b": right[0]}


add_version = store.add_version
history = store.history
save_run = store.save_run
verdict = store.verdict
approval = store.approval
decide = store.decide
get_run = store.get_run
get_approvals = store.get_approvals
get_verdict = store.get_verdict
