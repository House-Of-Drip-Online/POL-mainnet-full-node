"""Keep build, fixtures and commissioning inputs out of operational startup."""
import os
from collections.abc import Mapping


def assert_operational_configuration(env: Mapping[str, str] | None = None) -> None:
    env = os.environ if env is None else env
    if env.get("OMEGA_CONFIGURATION_CONTEXT", "RUNTIME") != "RUNTIME":
        raise ValueError("OMEGA_RUNTIME_CONFIGURATION_CONTEXT_INVALID")
    if env.get("OMEGA_BUILD_AUTHORITY") or env.get("OMEGA_BUILD_SOURCE_SHA"):
        raise ValueError("OMEGA_RUNTIME_BUILD_CONFIGURATION_FORBIDDEN")
    if env.get("NODE_ENV") == "test":
        raise ValueError("OMEGA_RUNTIME_TEST_CONFIGURATION_FORBIDDEN")
    if (env.get("OMEGA_COMMISSIONING_REQUIRED_OBSERVATIONS") or
            env.get("OMEGA_CERTIFICATION_WITNESS_REQUIRED_PASSES")):
        raise ValueError("OMEGA_RUNTIME_WITNESS_CONFIGURATION_FORBIDDEN")
    if env is os.environ:
        os.environ["OMEGA_CONFIGURATION_CONTEXT"] = "RUNTIME"
