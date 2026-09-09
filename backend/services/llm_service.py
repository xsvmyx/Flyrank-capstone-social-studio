import asyncio
import importlib
import pkgutil
from pathlib import Path
from typing import List

from config.settings import logger
from services.agents.base_agent import BaseAgent
from services.agents.registry import get_registered_agents
from schemas.variant_schemas import GeneratedVariant


class LLMService:
    """
    LLM orchestration service based on the decorated agents registry (@register_agent).
    Handles dynamic discovery, instantiation, and parallel execution of LLM agents.
    """

    def __init__(self):
        self._load_agent_modules()
        self._agents: List[BaseAgent] = self._instantiate_agents()

    def _load_agent_modules(self) -> None:
        """
        Dynamically scans and imports modules inside the agents directory.
        Importing these files triggers the execution of the @register_agent decorators.
        """
        agents_dir = Path(__file__).resolve().parent / "agents"

        for _, module_name, is_pkg in pkgutil.iter_modules([str(agents_dir)]):
            if not is_pkg and module_name not in ("base_agent", "registry", "schemas"):
                importlib.import_module(f"services.agents.{module_name}")

    def _instantiate_agents(self) -> List[BaseAgent]:
        """
        Retrieves all agent classes registered via the decorator and instantiates them.
        """
        agent_classes = get_registered_agents()
        instances = [agent_cls() for agent_cls in agent_classes]

        logger.info(
            f"🧩 LLMService initialized with {len(instances)} registered agent(s): "
            f"{[a.platform_name for a in instances]}"
        )
        return instances

    async def generate_all_variants(self, source_text: str) -> List[GeneratedVariant]:
            """
            Executes Groq API requests concurrently for all registered agents.
            """
            if not self._agents:
                logger.warning("⚠️ No agents registered with @register_agent.")
                return []

            logger.info(f"🚀 Triggering Groq generation across {len(self._agents)} agent(s) concurrently...")

            # Parallel execution across all loaded agents
            tasks = [agent.generate_variant(source_text) for agent in self._agents]
            
            
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_variants: List[GeneratedVariant] = []

            for result in raw_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ An agent failed during generation: {result}", exc_info=result)
                    continue

                
                logger.info(
                    f"\n--- [GENERATED VARIANT: {result.platform.upper()}] ---\n"
                    f"{result.content}\n"
                    f"-----------------------------------"
                )
                successful_variants.append(result)

            return successful_variants