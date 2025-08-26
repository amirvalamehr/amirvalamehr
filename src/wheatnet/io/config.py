from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
import json
import os

from wheatnet.engine.boolean_network import BooleanNetwork


def _read_json(path: str):
	with open(path, "r", encoding="utf-8") as f:
		return json.load(f)


def load_model(path: str) -> BooleanNetwork:
	data = _read_json(path)
	nodes = data.get("nodes", [])
	inputs = data.get("inputs", [])
	rules = data.get("rules", {})
	if not isinstance(nodes, list) or not isinstance(inputs, list) or not isinstance(rules, dict):
		raise ValueError("Model JSON must contain 'nodes' (list), 'inputs' (list), and 'rules' (object)")
	return BooleanNetwork(nodes=nodes, inputs=inputs, rules=rules)


def load_initial_state(path: Optional[str]) -> Optional[Dict[str, bool]]:
	if not path:
		return None
	data = _read_json(path)
	if not isinstance(data, dict):
		raise ValueError("Initial state must be a JSON object of name->bool")
	return {str(k): bool(v) for k, v in data.items()}


def load_input_schedule(path: Optional[str]) -> (Optional[List[Dict[str, bool]]], Optional[Dict[str, bool]]):
	if not path:
		return None, None
	data = _read_json(path)
	if isinstance(data, list):
		seq: List[Dict[str, bool]] = []
		for item in data:
			if not isinstance(item, dict):
				raise ValueError("Each schedule item must be an object of input->bool")
			seq.append({str(k): bool(v) for k, v in item.items()})
		return seq, None
	if isinstance(data, dict):
		return None, {str(k): bool(v) for k, v in data.items()}
	raise ValueError("Input schedule must be either an object (constant) or an array (per-step)")