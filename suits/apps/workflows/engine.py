from apps.jobs.models import Job
from .models import WorkflowStep
from django.db import transaction
from apps.audit.services import log_action


class WorkflowEngine:

    @staticmethod
    @transaction.atomic
    def move_to_next_step(job_id):
        # Lock the job row for update
        job = Job.objects.select_for_update().get(id=job_id)

        # Capture previous step
        previous_step = job.current_step.step_name if job.current_step else None

        # Determine next step
        steps = WorkflowStep.objects.filter(
            workflow_template=job.workflow_template
        ).order_by("step_order")

        if not job.current_step:
            next_step = steps.first()
        else:
            next_step = steps.filter(
                step_order=job.current_step.step_order + 1
            ).first()

        if not next_step:
            raise Exception("No next step available")

        # Validate transition rules
        WorkflowEngine.validate_transition(job, next_step)

        # Update job to next step
        job.current_step = next_step
        job.status = next_step.step_name
        job.save()

        # Log the workflow transition
        log_action(
            action="TRANSITION",
            instance=job,
            before={"step": previous_step},
            after={"step": job.current_step.step_name}
        )

        return job

    @staticmethod
    def validate_transition(job, next_step):
        if next_step.requires_attachment:
            if not hasattr(job, "attachments") or not job.attachments.exists():
                raise Exception("Attachment required for this step")