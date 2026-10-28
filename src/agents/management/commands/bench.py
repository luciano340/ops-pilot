import asyncio
from argparse import ArgumentParser
from collections.abc import Sequence
from io import StringIO
from time import perf_counter
from typing import Any

from django.core.management import BaseCommand, CommandError, call_command
from django.db import DatabaseError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.factory import ModelConfigurationError, create_model
from agents.plan_and_execute import MAX_ITERATIONS, PlanAndExecuteStrategy
from agents.react import ReactStrategy
from agents.schemas import BenchCommandInput
from agents.tools import get_agent_tools
from agents.types import StrategyResult
from bench import (
    SCENARIOS,
    BenchmarkResult,
    ScenarioKey,
    StrategyName,
    capture_snapshot,
    validate_answer,
    validate_state,
)


class Command(BaseCommand):
    help = "Benchmark reasoning strategies against operational scenarios."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--scenario",
            "-s",
            default="all",
            help="Scenario to run: c1, c2, c3, or all.",
        )
        parser.add_argument(
            "--strategies",
            default="react,plan_and_execute",
            help="Comma-separated strategy names.",
        )
        parser.add_argument(
            "--no-replanner",
            action="store_true",
            help="Skip Plan-and-Execute replanning and synthesize the final answer.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            raw_strategies = str(options["strategies"])
            strategies = [
                strategy.strip()
                for strategy in raw_strategies.split(",")
                if strategy.strip()
            ]
            command_input = BenchCommandInput(
                scenario=options["scenario"],
                strategies=strategies,
                no_replanner=options["no_replanner"],
            )
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc

        scenario_keys: list[ScenarioKey] = (
            list(SCENARIOS)
            if command_input.scenario == "all"
            else [command_input.scenario]
        )
        strategy_names: list[StrategyName] = command_input.strategies
        results: list[BenchmarkResult] = []

        try:
            model = create_model()
        except ModelConfigurationError as exc:
            raise CommandError(str(exc)) from exc

        with asyncio.Runner() as runner:
            try:
                for scenario_key in scenario_keys:
                    scenario = SCENARIOS[scenario_key]
                    for strategy_name in strategy_names:
                        try:
                            call_command("seed_db", verbosity=0, stdout=StringIO())
                            baseline = capture_snapshot()
                        except DatabaseError as exc:
                            raise CommandError(
                                f"Failed to seed or snapshot benchmark state: {exc}"
                            ) from exc
                        try:
                            strategy_result, latency_ms = runner.run(
                                self._run_strategy(
                                    strategy_name,
                                    scenario.request,
                                    command_input.no_replanner,
                                    model,
                                )
                            )
                        except ModelConfigurationError as exc:
                            raise CommandError(str(exc)) from exc
                        except StructuredOutputError as exc:
                            raise CommandError(str(exc)) from exc
                        except DatabaseError as exc:
                            raise CommandError(
                                "Database operation failed during strategy "
                                f"execution: {exc}"
                            ) from exc

                        try:
                            after = capture_snapshot()
                        except DatabaseError as exc:
                            raise CommandError(
                                f"Failed to read benchmark state after execution: {exc}"
                            ) from exc
                        errors = validate_answer(
                            scenario_key,
                            strategy_result.answer,
                            baseline,
                        )
                        errors.extend(validate_state(scenario_key, baseline, after))
                        results.append(
                            BenchmarkResult(
                                scenario=scenario_key,
                                strategy=strategy_name,
                                passed=not errors,
                                llm_calls=strategy_result.metrics.llm_calls,
                                latency_ms=latency_ms,
                                details="; ".join(errors),
                            )
                        )
            finally:
                runner.run(model.root_async_client.close())

        self.stdout.write(self._format_results(results))
        failures = [
            result for result in results if not result.passed
        ]
        for result in failures:
            self.stdout.write(
                f"{result.scenario}/{result.strategy}: {result.details}"
            )
        if failures:
            raise CommandError(
                f"{len(failures)} benchmark case(s) failed validation."
            )

    @staticmethod
    def _build_strategy(
        name: StrategyName,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        no_replanner: bool,
    ) -> ReasoningStrategy:
        if name == "react":
            return ReactStrategy(model, tools)
        return PlanAndExecuteStrategy(
            model,
            tools,
            max_iterations=MAX_ITERATIONS,
            no_replanner=no_replanner,
        )

    async def _run_strategy(
        self,
        name: StrategyName,
        request: str,
        no_replanner: bool,
        model: BaseChatModel,
    ) -> tuple[StrategyResult, float]:
        strategy = self._build_strategy(
            name,
            model,
            get_agent_tools(),
            no_replanner,
        )
        started = perf_counter()
        result = await strategy.run(request)
        latency_ms = (perf_counter() - started) * 1000
        return result, latency_ms

    @staticmethod
    def _format_results(results: list[BenchmarkResult]) -> str:
        columns = (
            "Cenário",
            "Estratégia",
            "Acerto",
            "Chamadas LLM",
            "Latência (ms)",
        )
        rows = [
            (
                result.scenario,
                result.strategy,
                "PASS" if result.passed else "FAIL",
                str(result.llm_calls),
                f"{result.latency_ms:.2f}",
            )
            for result in results
        ]
        widths = [
            max(len(columns[index]), *(len(row[index]) for row in rows))
            for index in range(len(columns))
        ]
        header = "| " + " | ".join(
            columns[index].ljust(widths[index]) for index in range(len(columns))
        ) + " |"
        separator = "|-" + "-|-".join("-" * width for width in widths) + "-|"
        body = [
            "| "
            + " | ".join(
                row[index].ljust(widths[index]) for index in range(len(columns))
            )
            + " |"
            for row in rows
        ]
        return "\n".join((header, separator, *body))
