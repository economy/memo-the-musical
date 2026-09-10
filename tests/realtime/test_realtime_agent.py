from pathlib import Path

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.services.message_dna_service import MessageDNAService
from memo.services.realtime_agent import RealtimeAgentFactory


def test_realtime_agent_has_one_server_side_state_tool(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    factory = RealtimeAgentFactory(MessageDNAService(repository))

    agent = factory.create("project_123")

    assert len(agent.tools) == 1
    assert agent.tools[0].name == "update_message_dna"
    assert isinstance(agent.instructions, str)
    assert "one high-value question at a time" in agent.instructions
    assert "exact facts" in agent.instructions
    assert "sensitive" in agent.instructions
    repository.close()
