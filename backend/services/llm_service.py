import asyncio
import importlib
import pkgutil
from pathlib import Path
from typing import List , Optional , Dict

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



    async def generate_variants(self, source_text: str) -> List[GeneratedVariant]:
            """
            Initial generation run: Executes Groq API requests concurrently
            for ALL registered agents without any exclusion or error context.
            """
            if not self._agents:
                logger.warning("⚠️ No agents registered with @register_agent.")
                return []

            logger.info(
                f"🚀 Triggering initial concurrent Groq generation for ALL {len(self._agents)} agent(s)..."
            )

            tasks = [agent.generate_variant(source_text) for agent in self._agents]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_variants: List[GeneratedVariant] = []

            for result in raw_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ An agent failed during initial generation: {result}", exc_info=result)
                    continue

                platform_str = str(result.platform).upper()
                logger.info(
                    f"\n--- [GENERATED VARIANT: {platform_str}] ---\n"
                    f"{result.content}\n"
                    f"-----------------------------------"
                )
                successful_variants.append(result)

            return successful_variants


    async def regenerate_variants(
            self, 
            source_text: str, 
            target_feedbacks: Dict[str, Optional[str]]
        ) -> List[GeneratedVariant]:
            """
            Regeneration run: Filters FOR targeted non-approved platforms, incorporates 
            their respective feedback/error messages, and triggers agent.regenerate_variant.
            """
            if not self._agents:
                logger.warning("⚠️ No agents registered with @register_agent.")
                return []

            
            target_map = {k.lower(): v for k, v in target_feedbacks.items()}

            
            agents_to_run = [
                agent for agent in self._agents
                if str(agent.platform_name).lower() in target_map
            ]

            if not agents_to_run:
                logger.info("⏩ All platforms are already approved or excluded. Nothing to regenerate.")
                return []

            logger.info(
                f"🔄 Triggering regeneration for {len(agents_to_run)} agent(s) "
                f"(Targets: {list(target_map.keys())})..."
            )

            
            tasks = [
                agent.regenerate_variant(
                    source_text=source_text, 
                    error_message=target_map.get(str(agent.platform_name).lower())
                ) 
                for agent in agents_to_run
            ]

            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_variants: List[GeneratedVariant] = []

            for result in raw_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ An agent failed during regeneration: {result}", exc_info=result)
                    continue

                platform_str = str(result.platform).upper()
                logger.info(
                    f"\n--- [REGENERATED VARIANT: {platform_str}] ---\n"
                    f"{result.content}\n"
                    f"-----------------------------------"
                )
                successful_variants.append(result)

            return successful_variants


        
