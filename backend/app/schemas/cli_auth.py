"""Schemas for DevArchAI CLI OAuth (PKCE + loopback)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CliAuthRegisterRequest(BaseModel):
    code_challenge: str = Field(..., min_length=43, max_length=128)
    code_challenge_method: str = Field(default="S256", pattern="^S256$")
    state: str = Field(..., min_length=16, max_length=128)
    redirect_uri: str = Field(..., min_length=10, max_length=512)
    device_name: str | None = Field(default=None, max_length=120)


class CliAuthRegisterResponse(BaseModel):
    session_id: str
    authorize_url: str
    expires_in: int


class CliAuthApproveRequest(BaseModel):
    session_id: str
    state: str


class CliAuthApproveResponse(BaseModel):
    redirect_uri: str


class CliAuthTokenRequest(BaseModel):
    session_id: str
    state: str
    code: str
    code_verifier: str = Field(..., min_length=43, max_length=128)


class CliAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    session_id: str
    email: str | None = None


class CliAuthRefreshRequest(BaseModel):
    refresh_token: str


class CliAuthRevokeRequest(BaseModel):
    refresh_token: str