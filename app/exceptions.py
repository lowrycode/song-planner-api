from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


SENSITIVE_FIELDS = {"password", "confirm_password", "hashed_password"}


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cleaned_errors = []

    for err in exc.errors():
        if "input" in err:
            input_val = err["input"]
            if isinstance(input_val, dict):
                input_copy = err["input"].copy()

                # Replace sensitive fields with ***
                for field in SENSITIVE_FIELDS:
                    if field in input_copy:
                        input_copy[field] = "***"

                err["input"] = input_copy

        # Remove the ctx field
        err.pop("ctx", None)

        cleaned_errors.append(err)

    return JSONResponse(
        status_code=422,
        content={"detail": cleaned_errors},
    )
