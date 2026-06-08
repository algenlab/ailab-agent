# Teaching Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional LLM post-processing layer that reads validated traces and enriches SceneGraph frames with teaching text and interactions without changing trace facts.

**Architecture:** `algolab.generation.teaching_enricher` builds compact trace contexts, calls the existing `llm_client.chat_json`, validates a strict overlay schema, and returns per-step teaching/interaction data. The pipeline applies the overlay after `compile_scene()` and before `validate_scene()`, while tests monkeypatch the LLM call.

**Tech Stack:** Python 3.10, Pydantic schemas already in `algolab.schemas`, existing `llm_client.chat_json`, pytest.

---

### Task 1: Overlay Module

**Files:**
- Create: `algolab/generation/teaching_enricher.py`
- Test: `tests/regression/teaching_enricher.py`

- [x] Write failing tests for safe overlay application and long-trace frame selection.
- [x] Run the focused regression tests and confirm they fail before implementation.
- [x] Implement context building, JSON schema validation, and SceneGraph overlay merge.
- [x] Run focused tests and targeted existing regression tests.

### Task 2: Pipeline Integration

**Files:**
- Modify: `algolab/pipeline.py`
- Test: `tests/regression/teaching_enricher.py`

- [x] Add opt-in teaching enrichment after scene compilation.
- [x] Keep failures non-blocking unless the core trace/scene validators fail.
- [x] Verify no trace event fields are modified by enrichment.
