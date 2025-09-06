"""
Neo4j Consistency Validation Engine

Implements 5-tier consistency checking system for novel world consistency
according to the LLD specifications.

Refactored to reuse the db/graph session factory, avoiding tight coupling to
an externally managed session. A session can still be injected for advanced
use-cases (e.g., batching multiple validations within a single transaction).
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

from neo4j import AsyncSession

from src.db.graph.session import create_neo4j_session

logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    """Consistency violation severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class ConsistencyViolation:
    """Represents a consistency violation."""

    rule_type: str
    severity: ViolationSeverity
    message: str
    affected_entities: list[str]
    auto_fixable: bool = False
    suggested_fix: str | None = None


@dataclass
class ConsistencyReport:
    """Consistency validation report."""

    violations: list[ConsistencyViolation]
    score: float  # 0-10 consistency score
    total_checks: int
    passed_checks: int

    @property
    def error_count(self) -> int:
        return len([v for v in self.violations if v.severity in (ViolationSeverity.ERROR, ViolationSeverity.FATAL)])

    @property
    def warning_count(self) -> int:
        return len([v for v in self.violations if v.severity == ViolationSeverity.WARNING])


class ConsistencyValidator:
    """Neo4j-based consistency validation engine."""

    def __init__(self, session: AsyncSession | None = None):
        # 可选注入会话；若未注入则按需通过 create_neo4j_session 创建
        self._session = session

    @asynccontextmanager
    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            # 复用外部传入的会话（不负责关闭）
            yield self._session
        else:
            async with create_neo4j_session() as session:
                yield session

    async def validate_all(self, novel_id: str) -> ConsistencyReport:
        """Run all consistency checks and return comprehensive report."""
        violations: list[ConsistencyViolation] = []
        total_checks = 0

        # Run all validation rules
        validators = [
            self._check_character_relationship_closure,
            self._check_world_rule_conflicts,
            self._check_timeline_consistency,
            self._check_character_attribute_continuity,
            self._check_geographic_spatial_reasonableness,
        ]

        for validator in validators:
            try:
                rule_violations = await validator(novel_id)
                violations.extend(rule_violations)
                total_checks += 1
                logger.debug(f"Completed {validator.__name__} for novel {novel_id}")
            except Exception as e:
                logger.error(f"Validation rule {validator.__name__} failed: {e}")
                violations.append(
                    ConsistencyViolation(
                        rule_type=validator.__name__,
                        severity=ViolationSeverity.ERROR,
                        message=f"Validation rule failed to execute: {e!s}",
                        affected_entities=[novel_id],
                    )
                )

        # Calculate consistency score (0-10)
        score = self._calculate_consistency_score(violations, total_checks)
        passed_checks = total_checks - len(
            [v for v in violations if v.severity in (ViolationSeverity.ERROR, ViolationSeverity.FATAL)]
        )

        return ConsistencyReport(
            violations=violations, score=score, total_checks=total_checks, passed_checks=passed_checks
        )

    async def _check_character_relationship_closure(self, novel_id: str) -> list[ConsistencyViolation]:
        """Check for missing transitive and symmetric character relationships."""
        violations = []

        # Check for missing symmetric relationships
        query_asymmetric = """
        MATCH (c1:Character {novel_id: $novel_id})-[r:RELATES_TO]->(c2:Character {novel_id: $novel_id})
        WHERE r.symmetric = true
        AND NOT EXISTS {
            MATCH (c2)-[r2:RELATES_TO]->(c1)
            WHERE r2.type = r.type
        }
        RETURN c1.id as char1_id, c1.name as char1_name,
               c2.id as char2_id, c2.name as char2_name,
               r.type as rel_type
        """

        async with self._get_session() as session:
            result = await session.run(query_asymmetric, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="character_relationship_closure",
                    severity=ViolationSeverity.WARNING,
                    message=f"Missing symmetric relationship: {record['char1_name']} -> {record['char2_name']} ({record['rel_type']}) should be bidirectional",
                    affected_entities=[record["char1_id"], record["char2_id"]],
                    auto_fixable=True,
                    suggested_fix=f"Create reverse RELATES_TO relationship from {record['char2_name']} to {record['char1_name']}",
                )
            )

        # Check for potential transitive relationship gaps
        query_transitive = """
        MATCH (c1:Character {novel_id: $novel_id})-[r1:RELATES_TO]->(c2:Character {novel_id: $novel_id})
        MATCH (c2)-[r2:RELATES_TO]->(c3:Character {novel_id: $novel_id})
        WHERE c1 <> c3
        AND r1.type = r2.type
        AND r1.strength >= 7 AND r2.strength >= 7
        AND NOT EXISTS {
            MATCH (c1)-[r3:RELATES_TO]->(c3)
            WHERE r3.type = r1.type
        }
        RETURN c1.id as char1_id, c1.name as char1_name,
               c2.id as char2_id, c2.name as char2_name,
               c3.id as char3_id, c3.name as char3_name,
               r1.type as rel_type
        """

        async with self._get_session() as session:
            result = await session.run(query_transitive, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="character_relationship_closure",
                    severity=ViolationSeverity.INFO,
                    message=f"Potential missing transitive relationship: {record['char1_name']} and {record['char3_name']} both strongly connected to {record['char2_name']} ({record['rel_type']})",
                    affected_entities=[record["char1_id"], record["char2_id"], record["char3_id"]],
                    auto_fixable=True,
                    suggested_fix=f"Consider adding {record['rel_type']} relationship between {record['char1_name']} and {record['char3_name']}",
                )
            )

        return violations

    async def _check_world_rule_conflicts(self, novel_id: str) -> list[ConsistencyViolation]:
        """Check for conflicting world rules."""
        violations = []

        # Find explicitly marked conflicts
        query_explicit = """
        MATCH (w1:WorldRule {novel_id: $novel_id})-[r:CONFLICTS_WITH]->(w2:WorldRule {novel_id: $novel_id})
        RETURN w1.id as rule1_id, w1.rule as rule1_text, w1.dimension as dim1,
               w2.id as rule2_id, w2.rule as rule2_text, w2.dimension as dim2,
               r.severity as severity
        """

        async with self._get_session() as session:
            result = await session.run(query_explicit, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            severity = (
                ViolationSeverity.ERROR
                if record["severity"] == "critical"
                else ViolationSeverity.ERROR
                if record["severity"] == "major"
                else ViolationSeverity.WARNING
            )

            violations.append(
                ConsistencyViolation(
                    rule_type="world_rule_conflicts",
                    severity=severity,
                    message=f"Rule conflict in {record['dim1']}/{record['dim2']}: '{record['rule1_text'][:50]}...' conflicts with '{record['rule2_text'][:50]}...'",
                    affected_entities=[record["rule1_id"], record["rule2_id"]],
                    auto_fixable=False,
                    suggested_fix="Review and resolve conflicting world rules - may require manual decision",
                )
            )

        # Check for same-dimension rules with conflicting constraints
        query_implicit = """
        MATCH (w1:WorldRule {novel_id: $novel_id}), (w2:WorldRule {novel_id: $novel_id})
        WHERE w1.dimension = w2.dimension
        AND w1.id <> w2.id
        AND w1.priority = w2.priority
        AND w1.rule CONTAINS 'must' AND w2.rule CONTAINS 'must not'
        RETURN w1.id as rule1_id, w1.rule as rule1_text,
               w2.id as rule2_id, w2.rule as rule2_text,
               w1.dimension as dimension
        """

        async with self._get_session() as session:
            result = await session.run(query_implicit, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="world_rule_conflicts",
                    severity=ViolationSeverity.ERROR,
                    message=f"Implicit rule conflict in {record['dimension']}: conflicting 'must'/'must not' statements",
                    affected_entities=[record["rule1_id"], record["rule2_id"]],
                    auto_fixable=False,
                    suggested_fix="Resolve conflicting mandatory rules in the same dimension",
                )
            )

        return violations

    async def _check_timeline_consistency(self, novel_id: str) -> list[ConsistencyViolation]:
        """Check for timeline and causality violations."""
        violations = []

        # Check for causal loops
        query_loops = """
        MATCH path = (e1:Event {novel_id: $novel_id})-[:CAUSES*2..10]->(e1)
        RETURN e1.id as event_id, e1.description as event_desc, length(path) as loop_length
        """

        async with self._get_session() as session:
            result = await session.run(query_loops, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="timeline_consistency",
                    severity=ViolationSeverity.ERROR,
                    message=f"Causal loop detected: Event '{record['event_desc'][:50]}...' causes itself through {record['loop_length']} steps",
                    affected_entities=[record["event_id"]],
                    auto_fixable=True,
                    suggested_fix="Remove one of the causal relationships to break the loop",
                )
            )

        # Check for temporal ordering violations
        query_temporal = """
        MATCH (e1:Event {novel_id: $novel_id})-[:CAUSES]->(e2:Event {novel_id: $novel_id})
        WHERE e1.timestamp > e2.timestamp
        RETURN e1.id as cause_id, e1.description as cause_desc, e1.timestamp as cause_time,
               e2.id as effect_id, e2.description as effect_desc, e2.timestamp as effect_time
        """

        async with self._get_session() as session:
            result = await session.run(query_temporal, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="timeline_consistency",
                    severity=ViolationSeverity.ERROR,
                    message=f"Temporal violation: Cause '{record['cause_desc'][:30]}...' happens after effect '{record['effect_desc'][:30]}...'",
                    affected_entities=[record["cause_id"], record["effect_id"]],
                    auto_fixable=True,
                    suggested_fix="Adjust event timestamps to maintain causal order",
                )
            )

        return violations

    async def _check_character_attribute_continuity(self, novel_id: str) -> list[ConsistencyViolation]:
        """Check for unrealistic character attribute changes."""
        violations = []

        # Check for dramatic age changes between chapters
        query_age_jumps = """
        MATCH (c:Character {novel_id: $novel_id})-[:HAS_STATE]->(cs1:CharacterState)
        MATCH (c)-[:HAS_STATE]->(cs2:CharacterState)
        WHERE cs1.chapter + 1 = cs2.chapter
        AND abs(cs2.age - cs1.age) > 2
        RETURN c.id as char_id, c.name as char_name,
               cs1.chapter as chapter1, cs1.age as age1,
               cs2.chapter as chapter2, cs2.age as age2
        """

        async with self._get_session() as session:
            result = await session.run(query_age_jumps, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            age_change = abs(record["age2"] - record["age1"])
            violations.append(
                ConsistencyViolation(
                    rule_type="character_attribute_continuity",
                    severity=ViolationSeverity.WARNING,
                    message=f"Unusual age change for {record['char_name']}: {age_change} years between chapters {record['chapter1']}-{record['chapter2']}",
                    affected_entities=[record["char_id"]],
                    auto_fixable=True,
                    suggested_fix="Adjust age progression to be more realistic or add time skip explanation",
                )
            )

        return violations

    async def _check_geographic_spatial_reasonableness(self, novel_id: str) -> list[ConsistencyViolation]:
        """Check for impossible travel speeds and distances."""
        violations = []

        # Check for unrealistic travel between locations
        query_travel = """
        MATCH (c:Character {novel_id: $novel_id})-[r1:LOCATED_AT]->(l1:Location {novel_id: $novel_id})
        MATCH (c)-[r2:LOCATED_AT]->(l2:Location {novel_id: $novel_id})
        MATCH (c)-[:USES]->(t:Transportation)
        WHERE r1.timestamp < r2.timestamp
        AND l1 <> l2
        WITH c, l1, l2, t, r1.timestamp as start_time, r2.timestamp as end_time,
             sqrt(pow(l2.x - l1.x, 2) + pow(l2.y - l1.y, 2)) as distance
        WHERE distance / duration.inHours(start_time, end_time) > t.speed * 2
        RETURN c.id as char_id, c.name as char_name,
               l1.name as loc1_name, l2.name as loc2_name,
               distance, t.type as transport_type, t.speed as max_speed
        """

        async with self._get_session() as session:
            result = await session.run(query_travel, {"novel_id": novel_id})
            records = await result.data()

        for record in records:
            violations.append(
                ConsistencyViolation(
                    rule_type="geographic_spatial_reasonableness",
                    severity=ViolationSeverity.WARNING,
                    message=f"Impossible travel: {record['char_name']} traveled {record['distance']:.1f}km from {record['loc1_name']} to {record['loc2_name']} too fast for {record['transport_type']} (max speed: {record['max_speed']}km/h)",
                    affected_entities=[record["char_id"]],
                    auto_fixable=True,
                    suggested_fix="Adjust travel time, distance, or transportation method",
                )
            )

        return violations

    def _calculate_consistency_score(self, violations: list[ConsistencyViolation], total_checks: int) -> float:
        """Calculate overall consistency score (0-10)."""
        if total_checks == 0:
            return 10.0

        # Weight violations by severity
        penalty = 0.0
        for violation in violations:
            if violation.severity == ViolationSeverity.FATAL:
                penalty += 3.0
            elif violation.severity == ViolationSeverity.ERROR:
                penalty += 2.0
            elif violation.severity == ViolationSeverity.WARNING:
                penalty += 1.0
            elif violation.severity == ViolationSeverity.INFO:
                penalty += 0.2

        # Calculate score (maximum penalty reduces score to 0)
        max_penalty = total_checks * 2.0  # Assume average 2.0 penalty per check
        score = max(0.0, 10.0 - (penalty / max_penalty) * 10.0)

        return round(score, 1)


__all__ = ["ConsistencyValidator", "ConsistencyViolation", "ConsistencyReport", "ViolationSeverity"]
