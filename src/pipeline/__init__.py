"""Support Pipeline Automation: sort Iraqi-dialect support tickets and pre-draft replies.

Stages: clean -> classify + extract -> confidence gate -> route + priority -> draft -> human review.

Built so far: config loading, cleaning, confidence gate, routing, the model wrapper.
Next (week 2): classify + extract prompt; (week 3): drafting and the batch runner.
"""
