"""
Test case_documents parameter implementation.

This test verifies that the case_documents parameter is correctly
stored in the GPTResearcher instance.
"""

from gpt_researcher.agent import GPTResearcher


def test_case_documents_parameter():
    """Test case_documents parameter is stored correctly."""
    docs = {
        "motion": "/tmp/motion.txt",
        "complaint": "/tmp/complaint.txt",
        "attacks": "/tmp/ATTACKS.json"
    }
    
    researcher = GPTResearcher(
        query="Test query",
        case_documents=docs
    )
    
    assert researcher.case_documents == docs
    print("✅ Test passed: case_documents stored correctly")


def test_case_documents_defaults_to_empty_dict():
    """Test case_documents defaults to empty dict when not provided."""
    researcher = GPTResearcher(query="Test query")
    
    assert researcher.case_documents == {}
    print("✅ Test passed: case_documents defaults to empty dict")


def test_case_documents_with_context_packet():
    """Test case_documents works alongside context_packet."""
    context = {
        "parties": {"plaintiff": "Smith", "defendant": "Jones"},
        "jurisdiction": "Georgia"
    }
    
    docs = {
        "motion": "/tmp/motion.txt",
        "complaint": "/tmp/complaint.txt"
    }
    
    researcher = GPTResearcher(
        query="Test query",
        context_packet=context,
        case_documents=docs
    )
    
    assert researcher.context_packet == context
    assert researcher.case_documents == docs
    print("✅ Test passed: case_documents works with context_packet")


def test_case_documents_none_becomes_empty_dict():
    """Test case_documents=None is converted to empty dict."""
    researcher = GPTResearcher(
        query="Test query",
        case_documents=None
    )
    
    assert researcher.case_documents == {}
    print("✅ Test passed: case_documents=None becomes empty dict")


if __name__ == "__main__":
    print("Running case_documents parameter tests...\n")
    
    test_case_documents_parameter()
    test_case_documents_defaults_to_empty_dict()
    test_case_documents_with_context_packet()
    test_case_documents_none_becomes_empty_dict()
    
    print("\n✅ All tests passed!")

