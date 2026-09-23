from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path

# path to the local config file
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "vault_config.json"


@dataclass
class Identity:
    # unique id of the agent using the bridge
    agent_id: str

    # unique id of the user installation
    user_install_id: str


class IdentityProvider(ABC):
    """
    Provides identity information for the current agent.
    Different implementations can load the identity
    from a config file, HTTP session, OAuth, etc.
    """

    @abstractmethod
    def resolve(self) -> Identity:
        pass


class DefaultIdentityProvider(IdentityProvider):
    """
    Default implementation.
    Currently reads the identity from a local config file.
    """

    def __init__(self):
        # load the config once when the provider is created
        with open(CONFIG_PATH) as f:
            self.config = json.load(f)

    def resolve(self) -> Identity:
        # return the identity used by the bridge
        return Identity(
            agent_id=self.config["agentId"],
            user_install_id=self.config["userInstallId"],
        )