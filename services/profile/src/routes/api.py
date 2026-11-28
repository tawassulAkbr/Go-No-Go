from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from contracts import Profile, Verdict
from ..services import accounts, data

router = APIRouter()


def required(value):
    if value is None:
        raise HTTPException(404, "Record unavailable")
    return value


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class Run(BaseModel):
    user_id: str
    idea_id: str | None = None
    mode: Literal["discover", "validate"]
    state: str
    state_json: dict
    budget_json: dict


@router.post("/users", status_code=201)
def register(body: Credentials):
    return accounts.register(str(body.email), body.password)


@router.post("/users/authenticate")
def authenticate(body: Credentials):
    user = accounts.authenticate(str(body.email), body.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return user


@router.get("/users/{uid}/profile")
def get_profile(uid: str):
    return required(data.profile(uid))


@router.put("/users/{uid}/profile")
def put_profile(uid: str, body: Profile):
    if uid != body.user_id:
        raise HTTPException(422, "Profile owner mismatch")
    return required(data.profile(uid, body))


@router.post("/users/{uid}/ideas", status_code=201)
def new_idea(uid: str, body: dict):
    return data.add_version(uid, body)


@router.post("/users/{uid}/ideas/{idea}/versions", status_code=201)
def version(uid: str, idea: str, body: dict):
    return required(data.add_version(uid, body, idea))


@router.get("/users/{uid}/history")
@router.get("/users/{uid}/ideas")
def history(uid: str):
    return data.history(uid)


@router.get("/users/{uid}/ideas/{idea}/versions")
def versions(uid: str, idea: str):
    return data.history(uid, idea)


@router.get("/users/{uid}/compare")
def compare(uid: str, a: str, b: str):
    return required(data.compare(uid, a, b))


@router.put("/runs/{run_id}")
def run(run_id: str, body: Run):
    return required(data.save_run(run_id, body))


@router.post("/verdicts")
def verdict(body: Verdict):
    return required(data.verdict(body))


class Approval(BaseModel):
    run_id: str
    reason: str


class Decision(BaseModel):
    decision: bool


@router.post("/approvals", status_code=201)
def approval(body: Approval):
    return data.approval(body.run_id, body.reason)


@router.put("/approvals/{aid}")
def decide(aid: str, body: Decision):
    return required(data.decide(aid, body.decision))


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    return required(data.get_run(run_id))


@router.get("/runs/{run_id}/approvals")
def get_approvals(run_id: str):
    return data.get_approvals(run_id)


@router.get("/runs/{run_id}/verdict")
def get_verdict(run_id: str):
    return required(data.get_verdict(run_id))
