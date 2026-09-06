from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Long enough to matter, short enough not to push people toward reuse. Argon2
# handles the rest; there is no truncation to work around as there is with bcrypt.
MIN_PASSWORD_LENGTH = 10


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=512)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    # Not length-validated: a short password must fail as a wrong password, not
    # as a validation error that reveals the rule was never met.
    password: str = Field(max_length=512)


class AccountOut(BaseModel):
    id: str
    email: str
