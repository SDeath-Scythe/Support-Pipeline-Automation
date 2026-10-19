"""Support Pipeline Automation: sort Iraqi-dialect support tickets and pre-draft replies.

Stages: clean -> classify + extract -> confidence gate -> (re-check) -> route + priority
-> draft -> human review. `pipeline.run.process()` runs one ticket through all of them
and emits an event at every stage (used by the viewer, and later by logging).
"""
