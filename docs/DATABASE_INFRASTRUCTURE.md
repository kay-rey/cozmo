# Database Infrastructure Documentation

## Overview

The Enhanced Trivia System uses SQLite with async support for data persistence. The database infrastructure provides connection pooling, automatic schema management, migrations, backup/recovery, and comprehensive data models.

## Components

### DatabaseManager (`utils/database.py`)

The main database manager handles:

- Async SQLite connections with connection pooling
- Schema creation and versioning
- Database integrity checks
- Performance optimization with indexes

**Key Features:**

- Connection pooling (max 5 connections)
- Foreign key constraint enforcement
- Automatic schema initialization
- Database statistics and health monitoring

### Data Models (`utils/models.py`)

Comprehensive data models for all entities:

- **UserProfile**: User statistics and preferences
- **Question**: Trivia questions with metadata
- **UserAchievement**: Achievement tracking
- **WeeklyRanking**: Leaderboard data
- **GameSession**: Active game tracking

All models support serialization/deserialization for database storage.

### Migration System (`utils/migrations.py`)

Handles database schema updates:

- Version-based migrations
- Safe column additions
- Index creation utilities
- Rollback support

### Backup & Recovery (`utils/backup.py`)

Automated backup and recovery system:

- Daily and weekly automated backups
- Manual backup creation
- Database integrity verification
- Emergency recovery procedures
- Backup cleanup and retention

## Database Schema

### Tables

1. **users** - User profiles and statistics
2. **questions** - Trivia questions with metadata
3. **user_achievements** - Achievement tracking
4. **weekly_rankings** - Weekly leaderboard data
5. **game_sessions** - Active game tracking
6. **schema_version** - Database version tracking

### Indexes

Performance indexes on frequently queried columns:

- User points (DESC for leaderboards)
- Question difficulty and category
- Achievement lookups
- Game session tracking

## Usage

### Initialize Database

```python
from utils.database import db_manager

# Initialize database with schema
await db_manager.initialize_database()

# Check database health
integrity_ok = await db_manager.check_database_integrity()
```

### Basic Operations

```python
# Get connection from pool
async with db_manager.get_connection() as conn:
    # Insert user
    await conn.execute(
        "INSERT INTO users (user_id, total_points) VALUES (?, ?)",
        (user_id, points)
    )
    await conn.commit()

    # Query data
    cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = await cursor.fetchone()
```

### Backup Operations

```python
from utils.backup import BackupManager

backup_manager = BackupManager(db_manager)

# Create manual backup
backup_path = await backup_manager.create_backup("manual")

# Restore from backup
success = await backup_manager.restore_from_backup(backup_path)

# Start automatic backup scheduler
await backup_manager.schedule_automatic_backups()
```

## Configuration

### Database Location

- Default: `data/trivia.db`
- Backups: `data/backups/`

### Connection Pool

- Max connections: 5
- Auto-cleanup on close

### Backup Retention

- Keep 30 most recent backups
- Daily backups created automatically
- Weekly backups on Mondays

## Testing

Run the comprehensive test suite:

```bash
python tests/test_database_infrastructure.py
```

Tests cover:

- Database initialization
- CRUD operations
- Data model serialization
- Backup and recovery
- Connection pooling
- Database statistics

## Initialization Script

Use the initialization script for setup:

```bash
# Initialize fresh database
python utils/init_database.py

# Reset database (with backup)
python utils/init_database.py reset

# Test database operations
python utils/init_database.py test
```

## Error Handling

The database infrastructure includes comprehensive error handling:

- Connection failures with retry logic
- Database corruption detection
- Automatic backup before risky operations
- Graceful degradation on errors
- Detailed logging for troubleshooting

## Performance Considerations

- Connection pooling reduces overhead
- Indexes optimize common queries
- Async operations prevent blocking
- Regular integrity checks
- Efficient backup mechanisms

## Security

- Parameterized queries prevent SQL injection
- Foreign key constraints maintain data integrity
- Regular backups protect against data loss
- Database file permissions properly set
