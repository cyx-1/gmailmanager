"""Tests for the main module."""

import pytest
from main import get_gmail_service, main

def test_get_gmail_service_error(monkeypatch):
    """Test get_gmail_service when an error occurs."""
    def mock_from_client_secrets_file(*args, **kwargs):
        raise Exception('Test error')
    
    monkeypatch.setattr(
        'main.InstalledAppFlow.from_client_secrets_file',
        mock_from_client_secrets_file
    )
    
    with pytest.raises(Exception):
        get_gmail_service()

@pytest.fixture
def mock_gmail_service(monkeypatch):
    """Fixture to create a mock Gmail service."""
    class MockService:
        def __init__(self, labels=None):
            self.labels = labels or []
        
        def users(self):
            return self
            
        def labels(self):
            return self
            
        def list(self, userId='me'):
            return self
            
        def execute(self):
            return {'labels': self.labels}
    
    return MockService

def test_main_no_labels(capsys, monkeypatch, mock_gmail_service):
    """Test main function when no labels are found."""
    service = mock_gmail_service()
    monkeypatch.setattr('main.get_gmail_service', lambda: service)
    
    main()
    captured = capsys.readouterr()
    assert 'No labels found.' in captured.out

def test_main_with_labels(capsys, monkeypatch, mock_gmail_service):
    """Test main function with mock labels."""
    labels = [{'name': 'INBOX'}, {'name': 'SENT'}]
    service = mock_gmail_service(labels)
    monkeypatch.setattr('main.get_gmail_service', lambda: service)
    
    main()
    captured = capsys.readouterr()
    assert 'Labels:' in captured.out
    assert '- INBOX' in captured.out
    assert '- SENT' in captured.out 