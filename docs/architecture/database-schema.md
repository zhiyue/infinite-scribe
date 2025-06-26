# Database Schema

## PostgreSQL
```sql
-- Novels Table
CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    theme TEXT,
    writing_style TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'GENESIS' CHECK (status IN ('GENESIS', 'GENERATING', 'PAUSED', 'COMPLETED', 'FAILED')),
    target_chapters INTEGER NOT NULL DEFAULT 0,
    completed_chapters INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chapters Table
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(255),
    content_url TEXT, -- URL to content in Minio
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'REVIEWING', 'REVISING', 'PUBLISHED')),
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (novel_id, chapter_number)
);

-- Characters Table
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('PROTAGONIST', 'ANTAGONIST', 'ALLY', 'SUPPORTING')),
    description TEXT,
    background_story TEXT,
    personality_traits TEXT[], -- Array of strings
    goals TEXT[], -- Array of strings
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Worldview Entries Table (Stores attributes of worldview entities)
CREATE TABLE worldview_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- This ID will match the Neo4j node's app_id property
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    entry_type VARCHAR(50) NOT NULL CHECK (entry_type IN ('LOCATION', 'ORGANIZATION', 'TECHNOLOGY', 'LAW', 'CONCEPT', 'EVENT', 'ITEM')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (novel_id, name, entry_type) 
);

-- Reviews Table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL, 
    review_type VARCHAR(50) NOT NULL CHECK (review_type IN ('CRITIC', 'FACT_CHECK')),
    score NUMERIC(3, 1), 
    comment TEXT, 
    is_consistent BOOLEAN, 
    issues_found TEXT[], 
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Story Arcs Table
CREATE TABLE story_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    start_chapter_number INTEGER,
    end_chapter_number INTEGER,
    status VARCHAR(50) DEFAULT 'PLANNED' CHECK (status IN ('PLANNED', 'ACTIVE', 'COMPLETED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_characters_novel_id ON characters(novel_id);
CREATE INDEX idx_worldview_entries_novel_id ON worldview_entries(novel_id);
CREATE INDEX idx_reviews_chapter_id ON reviews(chapter_id);
CREATE INDEX idx_story_arcs_novel_id ON story_arcs(novel_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to relevant tables
CREATE TRIGGER set_timestamp_novels
BEFORE UPDATE ON novels
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_chapters
BEFORE UPDATE ON chapters
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_characters
BEFORE UPDATE ON characters
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_worldview_entries
BEFORE UPDATE ON worldview_entries
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_story_arcs
BEFORE UPDATE ON story_arcs
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
```

## Neo4j
*   **核心原则:** Neo4j用于存储和查询**每个小说项目内部的**知识图谱，包括世界观实体、角色及其之间的复杂关系和随时间演变的互动。所有Neo4j中的节点都应有一个 `app_id` 属性，该属性的值对应其在PostgreSQL中对应表的主键ID，以便于跨数据库关联。
*   **节点标签 (Node Labels) - 示例:**
    *   `:Novel` (属性: `app_id: string` (来自PG `novels.id`), `title: string`)
    *   `:Chapter` (属性: `app_id: string` (来自PG `chapters.id`), `chapter_number: integer`, `title: string`)
    *   `:Character` (属性: `app_id: string` (来自PG `characters.id`), `name: string`, `role: string`)
    *   `:WorldviewEntry` (属性: `app_id: string` (来自PG `worldview_entries.id`), `name: string`, `entry_type: string` (如 'LOCATION', 'ORGANIZATION', 'ITEM'))
    *   `:StoryArc` (属性: `app_id: string` (来自PG `story_arcs.id`), `title: string`)
    *   `:PlotPoint` (属性: `description: string`, `significance: float`) - (可选，用于更细致的情节跟踪)
*   **关系类型 (Relationship Types) - 示例 (所有关系都应隐含地属于某个Novel的上下文):**
    *   `(:Chapter)-[:BELONGS_TO_NOVEL]->(:Novel)`
    *   `(:Character)-[:APPEARS_IN_NOVEL]->(:Novel)`
    *   `(:WorldviewEntry)-[:PART_OF_NOVEL_WORLDVIEW]->(:Novel)`
    *   `(:StoryArc)-[:PART_OF_NOVEL_PLOT]->(:Novel)`
    *   **世界观内部关系:**
        *   `(:WorldviewEntry {entry_type:'LOCATION'})-[:CONTAINS_LOCATION]->(:WorldviewEntry {entry_type:'LOCATION'})`
        *   `(:WorldviewEntry {entry_type:'ORGANIZATION'})-[:HAS_MEMBER]->(:Character)`
        *   `(:WorldviewEntry {entry_type:'TECHNOLOGY'})-[:DERIVED_FROM]->(:WorldviewEntry {entry_type:'CONCEPT'})`
    *   **角色间关系 (可带属性，如章节号、关系强度/类型):**
        *   `(:Character)-[:KNOWS {since_chapter: 3, strength: 'strong'}]->(:Character)`
        *   `(:Character)-[:ALLIED_WITH {details: "Temporary alliance for mission X"}]->(:Character)`
        *   `(:Character)-[:ROMANTIC_INTEREST_IN]->(:Character)`
    *   **角色与世界观/章节互动:**
        *   `(:Character)-[:VISITED_LOCATION {chapter: 5, purpose: "Gather info"}]->(:WorldviewEntry {entry_type:'LOCATION'})`
        *   `(:Character)-[:USED_ITEM {chapter: 7}]->(:WorldviewEntry {entry_type:'ITEM'})`
        *   `(:Chapter)-[:FEATURES_CHARACTER_ACTION {action_description: "Saved the cat"}]->(:Character)`
        *   `(:Chapter)-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry)`
    *   **情节与章节/角色关联:**
        *   `(:Chapter)-[:ADVANCES_ARC]->(:StoryArc)`
        *   `(:PlotPoint)-[:OCCURS_IN_CHAPTER]->(:Chapter)`
        *   `(:PlotPoint)-[:INVOLVES_CHARACTER]->(:Character)`
*   **索引:** 将为常用的查询属性（如 `app_id`, `name`, `entry_type`）创建索引。
