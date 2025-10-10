from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic


def test_events_config_genesis_mapping():
    assert build_event_type("GENESIS", "Round.Created") == "Genesis.Session.Round.Created"
    assert build_event_type("genesis", "Stage.Confirmed") == "Genesis.Session.Stage.Confirmed"
    assert get_aggregate_type("GENESIS") == "GenesisSession"
    assert get_domain_topic("GENESIS") == "genesis.session.events"


def test_events_config_defaults():
    # Unknown scope falls back to Conversation defaults
    assert build_event_type("UNKNOWN", "X.Requested") == "Conversation.Session.X.Requested"
    assert get_aggregate_type("UNKNOWN") == "ConversationSession"
    assert get_domain_topic("UNKNOWN") == "conversation.session.events"
