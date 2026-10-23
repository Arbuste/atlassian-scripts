import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().with_name("environment_config.json")


def get_environment(key, environment_type="cloud", service_account=False):
    """Load an environment profile with human or Atlassian service-account URLs."""
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8-sig") as config_file:
            config = json.load(config_file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Environment config not found: {_CONFIG_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in environment config: {_CONFIG_PATH}") from exc

    environments = config.get("environments")
    if not isinstance(environments, dict):
        raise RuntimeError("Environment config must contain an 'environments' object.")
    profiles = environments.get(environment_type)
    if not isinstance(profiles, dict):
        available_types = ", ".join(sorted(k for k, v in environments.items() if isinstance(v, dict)))
        raise KeyError(f"Unknown environment type '{environment_type}'. Available types: {available_types}")
    if key not in profiles:
        available = ", ".join(sorted(profiles))
        raise KeyError(f"Unknown {environment_type} environment key '{key}'. Available keys: {available}")

    environment = dict(profiles[key])
    for application in ("jira", "confluence"):
        environment[f"{application}_base_url"] = get_base_url(
            environment, application, service_account=service_account
        )
    return environment


def get_base_url(environment, application, service_account=False):
    """Resolve a human URL from the profile or a service-account gateway URL."""
    application = application.lower()
    if application not in {"jira", "confluence"}:
        raise ValueError("application must be 'jira' or 'confluence'.")
    if service_account:
        cloud_id = environment.get("cloud_id")
        if not cloud_id:
            raise ValueError("A cloud_id is required for Atlassian service-account URLs.")
        return f"https://api.atlassian.com/ex/{application}/{cloud_id}"
    return environment.get(f"{application}_base_url") or ""
