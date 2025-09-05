# Database Migration Guide

This guide covers database migration procedures for the Enhanced Trivia System, including schema updates, data preservation, and rollback procedures.

## Overview

The Enhanced Trivia System uses a versioned migration system to handle database schema changes while preserving existing user data. All migrations are designed to be:

- **Backward compatible** where possible
- **Atomic** (all changes succeed or all fail)
- **Reversible** through backup restoration
- **Verified** through integrity checks

## Migration System Architecture

### Schema Versioning

The system tracks schema versions in the `schema_version` table:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Migration Process Flow

1. **Pre-migration backup** - Automatic backup creation
2. **Integrity check** - Verify database health
3. **Migration execution** - Apply schema changes
4. **Post-migration verification** - Ensure changes applied correctly
5. **Backup creation** - Create post-migration backup

## Current Schema (Version 1)

### Core Tables

#### Users Table

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    questions_answered INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    daily_challenge_completed DATE,
    weekly_challenge_completed DATE,
    preferred_difficulty TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Questions Table

```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false', 'fill_blank')),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    category TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    options TEXT, -- JSON for multiple choice options
    answer_variations TEXT, -- JSON for fill-in-blank variations
    explanation TEXT,
    point_value INTEGER DEFAULT 0,
    times_asked INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### User Achievements Table

```sql
CREATE TABLE user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(user_id, achievement_id)
);
```

#### Weekly Rankings Table

```sql
CREATE TABLE weekly_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start DATE NOT NULL,
    points INTEGER DEFAULT 0,
    rank INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start)
);
```

#### Game Sessions Table

```sql
CREATE TABLE game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    question_id INTEGER,
    difficulty TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE,
    is_challenge BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE SET NULL
);
```

### Performance Indexes

```sql
-- User performance indexes
CREATE INDEX idx_users_total_points ON users (total_points DESC);
CREATE INDEX idx_users_last_played ON users (last_played);
CREATE INDEX idx_users_points_streak ON users (total_points DESC, current_streak DESC);

-- Question performance indexes
CREATE INDEX idx_questions_difficulty ON questions (difficulty);
CREATE INDEX idx_questions_category ON questions (category);
CREATE INDEX idx_questions_type ON questions (question_type);
CREATE INDEX idx_questions_difficulty_category ON questions (difficulty, category);
CREATE INDEX idx_questions_performance ON questions (times_asked, times_correct);

-- Achievement indexes
CREATE INDEX idx_user_achievements_user_id ON user_achievements (user_id);

-- Rankings indexes
CREATE INDEX idx_weekly_rankings_week_start ON weekly_rankings (week_start);
CREATE INDEX idx_weekly_rankings_points ON weekly_rankings (points DESC);
CREATE INDEX idx_weekly_rankings_week_rank ON weekly_rankings (week_start, rank);

-- Game session indexes
CREATE INDEX idx_game_sessions_channel_id ON game_sessions (channel_id);
CREATE INDEX idx_game_sessions_active ON game_sessions (is_completed, start_time);
CREATE INDEX idx_game_sessions_user_time ON game_sessions (user_id, start_time DESC);
```

## Migration Procedures

### Automated Migration

Use the migration script for standard deployments:

```bash
python scripts/migrate_database.py
```

This script will:

1. Create a pre-migration backup
2. Check database integrity
3. Apply necessary migrations
4. Verify the migration
5. Create a post-migration backup

### Manual Migration Steps

For custom or emergency migrations:

#### 1. Create Backup

```bash
python scripts/backup_restore.py backup --type pre_migration
```

#### 2. Check Current Version

```bash
sqlite3 data/trivia.db "SELECT MAX(version) FROM schema_version;"
```

#### 3. Apply Migration (Example for future v2)

```sql
-- Example migration to version 2
BEGIN TRANSACTION;

-- Add new column to users table
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';

-- Create new table for user preferences
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    theme TEXT DEFAULT 'default',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Update schema version
INSERT INTO schema_version (version) VALUES (2);

COMMIT;
```

#### 4. Verify Migration

```bash
python scripts/optimize_database.py
```

#### 5. Create Post-Migration Backup

```bash
python scripts/backup_restore.py backup --type post_migration
```

## Data Preservation Strategies

### User Data Protection

All migrations are designed to preserve:

- User statistics and progress
- Achievement unlocks
- Historical game data
- Ranking information

### Data Validation

Before and after each migration:

```python
async def validate_user_data(conn):
    """Validate critical user data integrity."""

    # Check user count
    cursor = await conn.execute("SELECT COUNT(*) FROM users")
    user_count = (await cursor.fetchone())[0]

    # Check for negative points (data corruption indicator)
    cursor = await conn.execute("SELECT COUNT(*) FROM users WHERE total_points < 0")
    negative_points = (await cursor.fetchone())[0]

    # Check achievement consistency
    cursor = await conn.execute("""
        SELECT COUNT(*) FROM user_achievements ua
        LEFT JOIN users u ON ua.user_id = u.user_id
        WHERE u.user_id IS NULL
    """)
    orphaned_achievements = (await cursor.fetchone())[0]

    return {
        'user_count': user_count,
        'negative_points': negative_points,
        'orphaned_achievements': orphaned_achievements
    }
```

### Foreign Key Integrity

All foreign key relationships are preserved:

- `user_achievements.user_id` → `users.user_id`
- `weekly_rankings.user_id` → `users.user_id`
- `game_sessions.user_id` → `users.user_id`
- `game_sessions.question_id` → `questions.id`

## Rollback Procedures

### Automatic Rollback

If migration fails, the system automatically attempts rollback:

```python
try:
    await run_migration()
except Exception as e:
    logger.error(f"Migration failed: {e}")
    await restore_from_backup(pre_migration_backup)
```

### Manual Rollback

#### 1. Stop the Bot

```bash
sudo systemctl stop trivia-bot  # Linux
# or
pkill -f bot.py  # Manual process
```

#### 2. Restore from Backup

```bash
python scripts/backup_restore.py restore data/backups/pre_migration_backup.db
```

#### 3. Verify Restoration

```bash
sqlite3 data/trivia.db "PRAGMA integrity_check;"
```

#### 4. Restart Bot

```bash
sudo systemctl start trivia-bot
```

## Testing Migrations

### Staging Environment

Always test migrations in staging:

1. **Copy production data**:

   ```bash
   cp data/trivia.db data/trivia_staging.db
   ```

2. **Run migration on staging**:

   ```bash
   DATABASE_PATH=data/trivia_staging.db python scripts/migrate_database.py
   ```

3. **Validate results**:
   ```bash
   DATABASE_PATH=data/trivia_staging.db python scripts/optimize_database.py
   ```

### Migration Testing Checklist

- [ ] Schema version updated correctly
- [ ] All existing data preserved
- [ ] Foreign key constraints maintained
- [ ] Indexes created successfully
- [ ] Performance not degraded
- [ ] Backup/restore works correctly

## Common Migration Scenarios

### Adding New Columns

```sql
-- Safe: Add column with default value
ALTER TABLE users ADD COLUMN new_column TEXT DEFAULT '';

-- Update existing records if needed
UPDATE users SET new_column = 'default_value' WHERE new_column IS NULL;
```

### Creating New Tables

```sql
-- Create table with proper constraints
CREATE TABLE new_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_new_table_user_id ON new_table (user_id);
```

### Modifying Existing Data

```sql
-- Use transactions for data modifications
BEGIN TRANSACTION;

-- Update data
UPDATE users SET total_points = total_points + bonus_points
WHERE user_id IN (SELECT user_id FROM bonus_eligible_users);

-- Verify changes
-- (Add verification queries here)

COMMIT;
```

## Performance Considerations

### Migration Performance

- **Large tables**: Consider batch processing for data updates
- **Index creation**: May take time on large datasets
- **Vacuum**: Run after major schema changes
- **Statistics**: Update after migration completion

### Minimizing Downtime

1. **Use WAL mode**: Allows reads during writes
2. **Batch operations**: Process large updates in chunks
3. **Defer index creation**: Create indexes after data migration
4. **Parallel processing**: Use multiple connections where safe

## Monitoring and Alerts

### Migration Monitoring

Monitor these metrics during migration:

- Database size changes
- Query performance
- Error rates
- Memory usage

### Alert Conditions

Set up alerts for:

- Migration failures
- Integrity check failures
- Backup creation failures
- Excessive migration time

## Future Migration Planning

### Version 2 Planned Changes

Potential future migrations may include:

- User timezone support
- Enhanced question metadata
- Performance analytics tables
- Social features (friends, groups)

### Migration Strategy

For major changes:

1. **Incremental approach**: Small, frequent migrations
2. **Feature flags**: Enable new features gradually
3. **Compatibility layers**: Support old and new schemas temporarily
4. **Data archival**: Move old data to archive tables

---

**Important**: Always test migrations thoroughly in a staging environment before applying to production data.
