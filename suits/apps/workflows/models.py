# apps/workflows/models.py
#
# HOW WORKFLOWS WORK IN THIS SYSTEM:
#
# A WorkflowTemplate is a blueprint for how a type of case moves through
# a law firm. It belongs to a tenant (law firm group).
#
# Example template: "Personal Injury Case"
#   Step 1: Initial Consultation
#   Step 2: Document Collection
#   Step 3: Case Review
#   Step 4: Negotiation
#   Step 5: Settlement / Closed
#
# WorkflowTransition defines the connections between steps — i.e., from
# which step can you go to which other step, and what is that move called.
#
# BRANCHING — ATTORNEY DRIVEN:
#   An attorney looks at their case and decides the next move based on their
#   professional judgment. The system does NOT auto-decide. It shows the
#   attorney the available next steps and they CHOOSE.
#
#   Example: Case is on "Case Review"
#     Option A — label: "Proceed to Negotiation"  → goes to Step 4
#     Option B — label: "Request More Documents"  → goes back to Step 2
#     Option C — label: "Escalate to Partner"     → goes to Step 3b "Partner Review"
#
#   The attorney picks one. The API accepts the transition_id they chose.
#   This mirrors how real legal case management works.
#
# NO priority field — the attorney chooses, not the system.
# NO condition_field / condition_value — no automated rule evaluation.

from django.db import models
from apps.core.models import BaseModel


class WorkflowTemplate(BaseModel):
    """
    A reusable workflow blueprint assigned to a tenant.
    One template can be attached to many cases.

    Example names:
      "Personal Injury"
      "Divorce Proceedings"
      "Commercial Contract Dispute"
    """
    name        = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    active      = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class WorkflowStep(BaseModel):
    """
    A single stage in a workflow.

    order determines the display order in the progress bar.
    Two steps in the same workflow cannot share an order number.

    requires_attachment: if True, a document must be uploaded to the
    case before any attorney can advance past this step.
    """
    workflow            = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name                = models.CharField(max_length=255)
    description         = models.TextField(null=True, blank=True,
                            help_text="Explain what happens at this step.")
    order               = models.PositiveIntegerField(
                            help_text="Display order in the progress bar. Must be unique per workflow.")
    requires_attachment = models.BooleanField(
                            default=False,
                            help_text="If checked, the attorney must upload a document before advancing.")

    class Meta:
        unique_together = ("workflow", "order")
        ordering        = ["order"]

    def __str__(self):
        return f"{self.workflow.name} › Step {self.order}: {self.name}"


class WorkflowTransition(BaseModel):
    """
    A possible move from one step to another — chosen by the attorney.

    The attorney sees the label as a button or option.
    They pick the one that matches their professional judgment about the case.

    EXAMPLE: Case is on "Case Review" (step 3)
      Transition A: label="Proceed to Negotiation",   from=step3, to=step4
      Transition B: label="Request More Documents",    from=step3, to=step2
      Transition C: label="Escalate to Partner Review",from=step3, to=step3b

    The attorney picks A, B, or C. The system just applies their choice.

    IMPORTANT: There are no automated rules, no conditions, no priority.
    The attorney is the decision-maker. RBAC (coming later) will control
    which roles are allowed to execute which transitions.
    """
    from_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
        help_text="The step the case is currently on.",
    )
    to_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
        help_text="The step the case will move to.",
    )
    label = models.CharField(
        max_length=200,
        help_text='What the attorney sees as a button. e.g. "Proceed to Negotiation"',
    )

    class Meta:
        # Prevent two transitions with the same label from the same step
        unique_together = ("from_step", "label")
        ordering        = ["from_step__order", "label"]

    def __str__(self):
        return f"{self.from_step.name} → {self.to_step.name} ({self.label})"