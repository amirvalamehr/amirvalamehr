from __future__ import annotations

import argparse
import csv
import random
from typing import Dict, List, Optional, Sequence, Mapping

from wheatnet.io.config import load_model, load_initial_state, load_input_schedule
from wheatnet.engine.boolean_network import BooleanNetwork


def _compute_headers(model: BooleanNetwork, rows: List[Dict[str, bool]]) -> List[str]:
	inputs_headers = sorted(list(model.inputs))
	nodes_headers = sorted([n for n in model.nodes if n not in model.inputs])
	# Filter to only those keys that appeared (defensive)
	present = set().union(*[row.keys() for row in rows]) if rows else set()
	headers = [k for k in inputs_headers + nodes_headers if k in present]
	# Append any stragglers deterministically
	for k in sorted(present - set(headers)):
		headers.append(k)
	return headers


def _write_csv(path: str, rows: List[Dict[str, bool]], headers: Sequence[str]) -> None:
	with open(path, "w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=list(headers))
		writer.writeheader()
		for row in rows:
			writer.writerow({k: int(1 if row.get(k, False) else 0) for k in headers})


def simulate_command(args: argparse.Namespace) -> int:
	model = load_model(args.model)
	initial = load_initial_state(args.initial)
	schedule, const_inputs = load_input_schedule(args.input_schedule)
	trace = model.simulate(
		steps=args.steps,
		initial_state=initial,
		input_schedule=schedule,
		constant_inputs=const_inputs,
		include_inputs_in_trace=True,
	)
	headers = _compute_headers(model, trace)
	if args.csv:
		_write_csv(args.csv, trace, headers)
	if args.print:
		print("\t".join(headers))
		for row in trace:
			print("\t".join("1" if row.get(k, False) else "0" for k in headers))
	return 0


def _evaluate_objective(trace: List[Dict[str, bool]], target: str, objective: str) -> float:
	if not trace:
		return 0.0
	if objective == "final":
		return 1.0 if trace[-1].get(target, False) else 0.0
	if objective == "sum":
		return float(sum(1 for row in trace if row.get(target, False)))
	if objective == "mean":
		return float(sum(1 for row in trace if row.get(target, False))) / float(len(trace))
	raise ValueError("Unknown objective; choose from: final, sum, mean")


def optimize_command(args: argparse.Namespace) -> int:
	model = load_model(args.model)
	initial = load_initial_state(args.initial)
	rng = random.Random(args.seed)
	best_score = float("-inf")
	best_const: Optional[Dict[str, bool]] = None
	best_sched: Optional[List[Dict[str, bool]]] = None
	for _ in range(args.iterations):
		if args.mode == "constant":
			const_inputs = {name: bool(rng.getrandbits(1)) for name in model.inputs}
			schedule = None
		else:
			# schedule mode
			schedule = []
			for _t in range(args.steps):
				schedule.append({name: bool(rng.getrandbits(1)) for name in model.inputs})
			const_inputs = None
		trace = model.simulate(
			steps=args.steps,
			initial_state=initial,
			input_schedule=schedule,
			constant_inputs=const_inputs,
			include_inputs_in_trace=True,
		)
		score = _evaluate_objective(trace, args.target, args.objective)
		if score > best_score:
			best_score = score
			best_const = const_inputs
			best_sched = schedule
	print(f"Best {args.objective} for {args.target}: {best_score}")
	if best_const is not None:
		print("Best constant inputs:")
		for k in sorted(best_const.keys()):
			print(f"  {k}: {int(best_const[k])}")
	if best_sched is not None:
		print("Best schedule (first 8 steps shown):")
		for idx, step in enumerate(best_sched[:8]):
			pairs = ", ".join(f"{k}={int(v)}" for k, v in sorted(step.items()))
			print(f"  t={idx}: {pairs}")
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		prog="wheatnet",
		description="Boolean regulatory network simulation for wheat sucrose/starch metabolism",
	)
	sub = parser.add_subparsers(dest="command", required=True)

	sim = sub.add_parser("simulate", help="Run a simulation")
	sim.add_argument("--model", required=True, help="Path to model JSON")
	sim.add_argument("--steps", type=int, default=16, help="Number of steps to simulate")
	sim.add_argument("--initial", help="Path to initial state JSON (optional)")
	sim.add_argument("--input-schedule", dest="input_schedule", help="Path to input schedule JSON (object or array)")
	sim.add_argument("--csv", help="Path to write CSV output")
	sim.add_argument("--print", action="store_true", help="Print tabular results to stdout")
	sim.set_defaults(func=simulate_command)

	op = sub.add_parser("optimize", help="Random search over inputs to maximize target")
	op.add_argument("--model", required=True, help="Path to model JSON")
	op.add_argument("--steps", type=int, default=16, help="Number of steps to simulate")
	op.add_argument("--initial", help="Path to initial state JSON (optional)")
	op.add_argument("--target", default="Starch", help="Node to optimize for (default: Starch)")
	op.add_argument("--objective", choices=["final", "sum", "mean"], default="final", help="Optimization objective")
	op.add_argument("--mode", choices=["constant", "schedule"], default="constant", help="Optimize constant inputs or per-step schedule")
	op.add_argument("--iterations", type=int, default=256, help="Number of random trials")
	op.add_argument("--seed", type=int, default=42, help="Random seed")
	op.set_defaults(func=optimize_command)
	return parser


def main(argv: Optional[List[str]] = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	return args.func(args)


if __name__ == "__main__":
	raise SystemExit(main())