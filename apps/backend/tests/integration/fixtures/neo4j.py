from collections.abc import Generator
from typing import Any

import pytest
from testcontainers.neo4j import Neo4jContainer


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[dict[str, str], Any, None]:
    """Provide Neo4j testcontainer configuration."""
    container = Neo4jContainer("neo4j:5")

    with container as c:
        yield {
            "host": c.get_container_host_ip(),
            "port": c.get_exposed_port(7687),
            "user": "neo4j",
            "password": c.password,
        }
