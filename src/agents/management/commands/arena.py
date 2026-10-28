import asyncio
from argparse import ArgumentParser, Namespace
from typing import Any

from django.core.management import BaseCommand, CommandError
from pydantic import ValidationError

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.factory import ModelConfigurationError, create_model
from agents.plan_and_execute import PlanAndExecuteStrategy
from agents.react import ReactStrategy
from agents.reflection import CritiqueEvaluator, CritiqueOutput, ReflectionStrategy
from agents.schemas import ArenaCommandInput
from agents.tools import get_agent_tools
from arena import format_results, run_strategies


class Command(BaseCommand):
    help = "Compare reasoning strategies for an operations request."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("request")
        parser.add_argument(
            "--strategies",
            default="react,plan_and_execute",
            help="Comma-separated strategy names.",
        )
        parser.add_argument("--max-iterations", type=int, default=8)

    def handle(self, *args: Any, **options: Any) -> None:
        namespace = Namespace(**options)
        raw_strategies = [
            item.strip() for item in namespace.strategies.split(",")
        ]
        try:
            command_input = ArenaCommandInput(
                request=namespace.request,
                strategies=raw_strategies,
                max_iterations=namespace.max_iterations,
            )
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc

        try:
            model = create_model()
            tools = get_agent_tools()
            strategies: list[ReasoningStrategy] = []
            reflection_evaluator: CritiqueEvaluator | None = None
            if any(
                strategy.startswith("reflect:")
                for strategy in command_input.strategies
            ):
                reflection_evaluator = model.with_structured_output(
                    CritiqueOutput
                )
            if "react" in command_input.strategies:
                strategies.append(ReactStrategy(model, tools))
            if "reflect:react" in command_input.strategies:
                assert reflection_evaluator is not None
                strategies.append(
                    ReflectionStrategy(
                        ReactStrategy(model, tools),
                        reflection_evaluator,
                    )
                )
            if "plan_and_execute" in command_input.strategies:
                strategies.append(
                    PlanAndExecuteStrategy(
                        model,
                        tools,
                        max_iterations=command_input.max_iterations,
                    )
                )
            if "reflect:plan_and_execute" in command_input.strategies:
                assert reflection_evaluator is not None
                strategies.append(
                    ReflectionStrategy(
                        PlanAndExecuteStrategy(
                            model,
                            tools,
                            max_iterations=command_input.max_iterations,
                        ),
                        reflection_evaluator,
                    )
                )
            results = asyncio.run(
                run_strategies(command_input.request, strategies)
            )
        except ModelConfigurationError as exc:
            raise CommandError(str(exc)) from exc
        except StructuredOutputError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(format_results(results))
