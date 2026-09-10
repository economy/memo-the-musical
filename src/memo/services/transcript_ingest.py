from memo.domain.message_dna.extraction import extract_message_dna_patch
from memo.domain.message_dna.models import FactStatus, Project
from memo.domain.message_dna.updates import FactCorrection, MessageDNAPatch
from memo.services.message_dna_service import MessageDNAService


class TranscriptIngestor:
    def __init__(self, service: MessageDNAService) -> None:
        self._service = service

    def ingest_text(self, project_id: str, text: str) -> Project | None:
        """Merge extracted Message DNA from stored brief plus new spoken text."""
        project = self._service.get_project(project_id)
        if project is None:
            return None
        source = "\n".join(
            part for part in (project.message_dna.original_request, text.strip()) if part
        )
        if not source:
            return None
        patch = extract_message_dna_patch(source)
        filtered = self._without_duplicate_facts(project, patch)
        if not self._has_updates(filtered):
            return project
        return self._service.update_project(project_id, filtered)

    @staticmethod
    def _without_duplicate_facts(project: Project, patch: MessageDNAPatch) -> MessageDNAPatch:
        active = {
            fact.key: fact.value
            for fact in project.message_dna.locked_facts
            if fact.status is FactStatus.ACTIVE
        }
        corrections = [
            FactCorrection(key=item.key, value=item.value)
            for item in patch.fact_corrections or []
            if active.get(item.key) != item.value
        ]
        data = patch.model_dump()
        data["fact_corrections"] = corrections or None
        if project.message_dna.original_request:
            data["original_request"] = None
        return MessageDNAPatch.model_validate(data)

    @staticmethod
    def _has_updates(patch: MessageDNAPatch) -> bool:
        return any(
            getattr(patch, field) not in (None, [], {}) for field in type(patch).model_fields
        )
