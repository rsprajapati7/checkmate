import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from checkmate_cli.shell import run_shell, _SLASH_COMMANDS
from checkmate_cli.api import ScanResponse


def test_slash_commands_exclusion():
    # Verify "/view" and "/v" are removed from list of completions
    assert "/view" not in _SLASH_COMMANDS
    assert "/v" not in _SLASH_COMMANDS
    assert "/reset" in _SLASH_COMMANDS
    assert "/rt" in _SLASH_COMMANDS


def test_reset_command_clears_active_document():
    # Create a mock Console
    mock_console = MagicMock()

    # Create a mock ScanResponse
    mock_scan_data = {
        "filename": "test_document.pdf",
        "file_type": "pdf",
        "page_count": 2,
        "is_scanned": False,
        "risk_tier": "GREEN",
        "final_score": 12.0,
        "job_id": "job_123",
        "pipelines": {
            "ela": {"score": 0.0, "flags": []},
            "metadata": {"score": 10.0, "flags": []},
            "seal": {"score": 0.0, "flags": []},
            "nlp": {"score": 0.0, "flags": []},
        }
    }
    mock_response = ScanResponse(mock_scan_data)

    # We will simulate inputs to run_shell:
    # 1. "/analyze test_document.pdf" -> load active doc
    # 2. "/reset"                     -> reset document & chat history
    # 3. "/exit"                      -> quit the shell
    input_prompts = []
    
    def mock_input(prompt):
        input_prompts.append(prompt)
        if len(input_prompts) == 1:
            return "/analyze test_document.pdf"
        elif len(input_prompts) == 2:
            return "/reset"
        else:
            return "/exit"

    # Mock all API dependencies called during /analyze
    with patch("checkmate_cli.shell.scan_document_sync", return_value=mock_response) as mock_scan, \
         patch("checkmate_cli.shell.ai_summary_stream_sync", return_value=["summary"]) as mock_summary, \
         patch("checkmate_cli.shell.generate_report_sync", return_value=(b"pdf_content", True)) as mock_report, \
         patch("checkmate_cli.shell.run_pipeline_progress") as mock_progress, \
         patch("checkmate_cli.shell.print_diagnostic_table") as mock_diag, \
         patch("checkmate_cli.shell.stream_ai_summary") as mock_stream_summary, \
         patch("builtins.input", side_effect=mock_input), \
         patch("sys.stdin.isatty", return_value=False), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.write_bytes") as mock_write:
        
        run_shell(mock_console)

        # Let's verify the calls
        mock_scan.assert_called_once_with(str(Path("test_document.pdf").resolve()))
        mock_report.assert_called_once_with(mock_response)

    # Let's verify the prompt sequence:
    # Prompt 1: CheckMate >> (initially no active doc)
    # Prompt 2: CheckMate [test_document.pdf] >> (active doc loaded)
    # Prompt 3: CheckMate >> (active doc reset on /reset)
    assert len(input_prompts) >= 3
    assert input_prompts[0] == "CheckMate >> "
    assert input_prompts[1] == "CheckMate [test_document.pdf] >> "
    assert input_prompts[2] == "CheckMate >> "
