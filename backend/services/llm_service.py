import importlib
import pkgutil
from pathlib import Path
from typing import List, Optional

from config.settings import logger
from services.agents.base_agent import BaseAgent
from services.agents.registry import get_registered_agents
from schemas.variant_schemas import GeneratedVariant, SocialPlatform


class LLMService:
    """
    LLM orchestration service based on the decorated agents registry (@register_agent).
    Handles dynamic discovery, instantiation, and execution of a specific platform agent.
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

    async def generate_variant_for_platform(
        self, source_text: str, platform: SocialPlatform , error_message= str
    ) -> Optional[GeneratedVariant]:
        """
        Finds the specific agent matching the platform and generates a single variant.
        """
        if not self._agents:
            logger.warning("⚠️ No agents registered with @register_agent.")
            return None

        
        target_platform_str = str(platform).lower()
        matching_agent = next(
            (agent for agent in self._agents if str(agent.platform_name).lower() == target_platform_str),
            None
        )

        if not matching_agent:
            logger.error(f"❌ No registered agent found for platform: {platform}")
            raise ValueError(f"Unsupported platform agent: {platform}")

        logger.info(f"🤖 Generating variant using agent for platform: {matching_agent.platform_name}...")

        try:
            result = await matching_agent.generate_variant(source_text,error_message)

            platform_str = str(result.platform).upper()
            logger.info(
                f"\n--- [GENERATED VARIANT: {platform_str}] ---\n"
                f"{result.content}\n"
                f"-----------------------------------"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Agent for {platform} failed during generation: {e}", exc_info=True)
            raise e


        
    # async def regenerate_variants(
    #         self, 
    #         source_text: str, 
    #         target_feedbacks: Dict[str, Optional[str]]
    #     ) -> List[GeneratedVariant]:
    #         """
    #         Regeneration run: Sequentially runs targeted agents to prevent 429 rate limits.
    #         """
    #         if not self._agents:
    #             logger.warning("⚠️ No agents registered with @register_agent.")
    #             return []

    #         target_map = {k.lower(): v for k, v in target_feedbacks.items()}

    #         agents_to_run = [
    #             agent for agent in self._agents
    #             if str(agent.platform_name).lower() in target_map
    #         ]

    #         if not agents_to_run:
    #             logger.info("⏩ All platforms are already approved or excluded. Nothing to regenerate.")
    #             return []

    #         logger.info(
    #             f"🔄 Triggering sequential regeneration for {len(agents_to_run)} agent(s) "
    #             f"(Targets: {list(target_map.keys())})..."
    #         )

    #         successful_variants: List[GeneratedVariant] = []

    #         for agent in agents_to_run:
    #             try:
                    
    #                 await asyncio.sleep(3)

    #                 logger.info(f"🤖 Regenerating variant for {agent.platform_name}...")
    #                 result = await agent.regenerate_variant(
    #                     source_text=source_text, 
    #                     error_message=target_map.get(str(agent.platform_name).lower())
    #                 )

    #                 platform_str = str(result.platform).upper()
    #                 logger.info(
    #                     f"\n--- [REGENERATED VARIANT: {platform_str}] ---\n"
    #                     f"{result.content}\n"
    #                     f"-----------------------------------"
    #                 )
    #                 successful_variants.append(result)

    #             except Exception as e:
    #                 logger.error(f"❌ An agent failed during regeneration: {e}", exc_info=e)
    #                 continue

    #         return successful_variants