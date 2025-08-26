from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set
import ast


class BooleanExpressionError(ValueError):
	pass


class _SafeBooleanEvaluator:
	"""Safely evaluates boolean expressions over named boolean variables.

	Supports: and, or, not, True, False, names, parentheses.
	"""

	ALLOWED_NODE_TYPES = (
		ast.Expression,
		ast.BoolOp,
		ast.UnaryOp,
		ast.Name,
		ast.Constant,
		ast.And,
		ast.Or,
		ast.Not,
		ast.Load,
	)

	def __init__(self, expression: str) -> None:
		self.expression = expression
		try:
			self._ast = ast.parse(expression, mode="eval")
		except SyntaxError as exc:
			raise BooleanExpressionError(f"Invalid boolean expression: {expression}") from exc
		self._validate_ast(self._ast)

	def _validate_ast(self, node: ast.AST) -> None:
		for child in ast.walk(node):
			if not isinstance(child, self.ALLOWED_NODE_TYPES):
				raise BooleanExpressionError(
					f"Disallowed syntax in expression '{self.expression}': {type(child).__name__}"
				)
			if isinstance(child, ast.Constant) and not isinstance(child.value, bool):
				raise BooleanExpressionError(
					f"Only boolean constants True/False are allowed in '{self.expression}'"
				)

	def evaluate(self, variables: Mapping[str, bool]) -> bool:
		return self._eval_node(self._ast.body, variables)

	def _eval_node(self, node: ast.AST, variables: Mapping[str, bool]) -> bool:
		if isinstance(node, ast.Name):
			if node.id not in variables:
				raise BooleanExpressionError(f"Unknown variable '{node.id}' in '{self.expression}'")
			return bool(variables[node.id])
		if isinstance(node, ast.Constant):
			return bool(node.value)
		if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
			return not self._eval_node(node.operand, variables)
		if isinstance(node, ast.BoolOp):
			values = [self._eval_node(v, variables) for v in node.values]
			if isinstance(node.op, ast.And):
				result = True
				for val in values:
					result = result and val
				return result
			if isinstance(node.op, ast.Or):
				result = False
				for val in values:
					result = result or val
				return result
		raise BooleanExpressionError(f"Unsupported expression fragment in '{self.expression}'")


@dataclass
class BooleanRule:
	target: str
	expression: str
	evaluator: _SafeBooleanEvaluator


class BooleanNetwork:
	"""Boolean regulatory network with synchronous updates."""

	def __init__(
		self,
		nodes: Iterable[str],
		inputs: Iterable[str],
		rules: Mapping[str, str],
	) -> None:
		self.nodes: Set[str] = set(nodes)
		self.inputs: Set[str] = set(inputs)
		self.rules: Dict[str, BooleanRule] = {}

		for target, expr in rules.items():
			if target not in self.nodes:
				raise ValueError(f"Rule defined for unknown node '{target}'")
			evaluator = _SafeBooleanEvaluator(expr)
			self.rules[target] = BooleanRule(target=target, expression=expr, evaluator=evaluator)

		self._validate_variables()

	def _validate_variables(self) -> None:
		known = self.nodes | self.inputs
		for rule in self.rules.values():
			for child in ast.walk(rule.evaluator._ast):
				if isinstance(child, ast.Name) and child.id not in known:
					raise BooleanExpressionError(
						f"Unknown variable '{child.id}' referenced in rule for '{rule.target}'"
					)

	def initial_state(self, seed_state: Optional[Mapping[str, bool]] = None) -> Dict[str, bool]:
		state: Dict[str, bool] = {name: False for name in self.nodes}
		if seed_state:
			for name, value in seed_state.items():
				if name in self.nodes:
					state[name] = bool(value)
		return state

	def step(
		self,
		state: Mapping[str, bool],
		external_inputs: Mapping[str, bool],
	) -> Dict[str, bool]:
		context: Dict[str, bool] = {**state, **external_inputs}
		new_state: Dict[str, bool] = dict(state)
		for node in self.nodes:
			if node in self.rules:
				new_state[node] = self.rules[node].evaluator.evaluate(context)
			else:
				new_state[node] = bool(state.get(node, False))
		return new_state

	def simulate(
		self,
		steps: int,
		initial_state: Optional[Mapping[str, bool]] = None,
		input_schedule: Optional[Sequence[Mapping[str, bool]]] = None,
		constant_inputs: Optional[Mapping[str, bool]] = None,
		include_inputs_in_trace: bool = True,
	) -> List[Dict[str, bool]]:
		if steps < 0:
			raise ValueError("steps must be non-negative")
		state = self.initial_state(initial_state)
		trace: List[Dict[str, bool]] = []
		for t in range(steps):
			inputs = self._resolve_inputs_for_step(t, input_schedule, constant_inputs)
			state = self.step(state, inputs)
			row = dict(state)
			if include_inputs_in_trace:
				for k, v in inputs.items():
					row[k] = bool(v)
			trace.append(row)
		return trace

	def _resolve_inputs_for_step(
		self,
		step_index: int,
		schedule: Optional[Sequence[Mapping[str, bool]]],
		constant_inputs: Optional[Mapping[str, bool]],
	) -> Dict[str, bool]:
		result: Dict[str, bool] = {name: False for name in self.inputs}
		if constant_inputs:
			for k, v in constant_inputs.items():
				if k in result:
					result[k] = bool(v)
		if schedule:
			idx = min(step_index, len(schedule) - 1)
			for k, v in schedule[idx].items():
				if k in result:
					result[k] = bool(v)
		return result