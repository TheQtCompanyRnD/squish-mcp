from pydantic import BaseModel
from pydantic import Field


class TestRunResponse(BaseModel):
    """Result of a Squish test execution."""

    stdout: str = Field(description="Standard output from squishrunner")
    stderr: str = Field(description="Standard error output from squishrunner")
