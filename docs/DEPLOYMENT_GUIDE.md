# Enhanced Trivia System - Deployment Guide

This guide provides comprehensive instructions for deploying the Enhanced Trivia System to production environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Database Migration](#database-migration)
3. [Backup Strategy](#backup-strategy)
4. [Performance Optimization](#performance-optimization)
5. [Production Configuration](#production-configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Rollback Procedures](#rollback-procedures)

## Pre-Deployment Checklist

### System Requirements

- Python 3.8 or higher
- SQLite 3.35 or higher (for JSON support)
- Minimum 1GB RAM
- Minimum 10GB disk space
- Discord Bot Token
- Stable internet connection

### Environment Setup

1. **Create production environment**:

   ```bash
   python -m venv venv_prod
   source venv_prod/bin/activate  # On Windows: venv_prod\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:

   ```bash
   export DISCORD_TOKEN="your_bot_token_here"
   export ENVIRONMENT="production"
   export LOG_LEVEL="INFO"
   ```

4. **Create data directories**:
   ```bash
   mkdir -p data/backups
   mkdir -p logs
   ```

## Database Migration

### Pre-Migration Steps

1. **Create backup of existing database**:

   ```bash
   python scripts/backup_restore.py backup --type pre_deployment
   ```

2. **Verify database integrity**:

   ```bash
   python scripts/optimize_database.py
   ```

3. **Check current schema version**:
   ```bash
   sqlite3 data/trivia.db "SELECT MAX(version) FROM schema_version;"
   ```

### Running Migration

1. **Execute migration script**:

   ```bash
   python scripts/migrate_database.py
   ```

2. **Verify migration success**:
   - Check logs for any errors
   - Verify schema version updated
   - Run integrity check

### Post-Migration Verification

1. **Test basic functionality**:

   ```bash
   python -c "
   import asyncio
   from utils.database import DatabaseManager

   async def test():
       db = DatabaseManager()
       async with db.get_connection() as conn:
           cursor = await conn.execute('SELECT COUNT(*) FROM users')
           print(f'Users: {(await cursor.fetchone())[0]}')

   asyncio.run(test())
   "
   ```

2. **Create post-migration backup**:
   ```bash
   python scripts/backup_restore.py backup --type post_migration
   ```

## Backup Strategy

### Automated Backups

The system includes automated backup scheduling:

- **Daily backups**: Created automatically at midnight
- **Weekly backups**: Created every Monday
- **Pre-migration backups**: Created before any schema changes

### Manual Backup Commands

```bash
# Create manual backup
python scripts/backup_restore.py backup --type manual

# List all backups
python scripts/backup_restore.py list

# Clean up old backups (keep 10 most recent)
python scripts/backup_restore.py cleanup --keep 10
```

### Backup Verification

All backups are automatically verified for integrity. To manually verify:

```bash
# Verify specific backup
sqlite3 backup_file.db "PRAGMA integrity_check;"
```

### Backup Storage Recommendations

1. **Local backups**: Stored in `data/backups/`
2. **Remote backups**: Consider copying to cloud storage
3. **Retention policy**: Keep 30 daily, 12 weekly, 12 monthly backups

## Performance Optimization

### Database Optimization

1. **Run optimization script**:

   ```bash
   python scripts/optimize_database.py
   ```

2. **Manual optimization steps**:

   ```bash
   # Update statistics
   sqlite3 data/trivia.db "ANALYZE;"

   # Vacuum database (if fragmentation > 10%)
   sqlite3 data/trivia.db "VACUUM;"
   ```

### Index Optimization

The system automatically creates performance indexes:

- User leaderboard queries
- Question filtering by difficulty/category
- Game session tracking
- Weekly rankings

### Memory Configuration

Recommended SQLite PRAGMA settings (automatically applied):

```sql
PRAGMA cache_size = -64000;      -- 64MB cache
PRAGMA journal_mode = WAL;       -- Write-Ahead Logging
PRAGMA synchronous = NORMAL;     -- Balance safety/performance
PRAGMA temp_store = MEMORY;      -- Use memory for temp tables
```

## Production Configuration

### Environment Variables

Create a `.env` file for production:

```bash
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id

# Database Configuration
DATABASE_PATH=data/trivia.db
BACKUP_RETENTION_DAYS=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/trivia_bot.log

# Performance Configuration
CONNECTION_POOL_SIZE=10
MAX_CONNECTION_POOL_SIZE=20
CONNECTION_TIMEOUT=30

# Backup Configuration
AUTO_BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=12
INTEGRITY_CHECK_INTERVAL_HOURS=6
```

### Logging Configuration

Create `logging.conf`:

```ini
[loggers]
keys=root,trivia

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_trivia]
level=INFO
handlers=consoleHandler,fileHandler
qualname=trivia
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=simpleFormatter
args=('logs/trivia_bot.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Systemd Service (Linux)

Create `/etc/systemd/system/trivia-bot.service`:

```ini
[Unit]
Description=Enhanced Trivia Discord Bot
After=network.target

[Service]
Type=simple
User=trivia
WorkingDirectory=/opt/trivia-bot
Environment=PATH=/opt/trivia-bot/venv/bin
ExecStart=/opt/trivia-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable trivia-bot
sudo systemctl start trivia-bot
```

## Monitoring and Maintenance

### Health Checks

1. **Database integrity check**:

   ```bash
   # Run every 6 hours via cron
   0 */6 * * * /opt/trivia-bot/scripts/health_check.py
   ```

2. **Backup verification**:
   ```bash
   # Verify latest backup daily
   0 2 * * * /opt/trivia-bot/scripts/verify_backups.py
   ```

### Log Monitoring

Monitor these log patterns:

- `ERROR`: Critical errors requiring immediate attention
- `WARNING`: Potential issues to investigate
- `Database connection error`: Connection pool issues
- `Backup failed`: Backup system problems

### Performance Monitoring

Key metrics to monitor:

- Database response times
- Memory usage
- Disk space usage
- Connection pool utilization
- Error rates

### Maintenance Schedule

**Daily**:

- Automated backups
- Log rotation
- Basic health checks

**Weekly**:

- Database optimization
- Backup cleanup
- Performance analysis

**Monthly**:

- Full system backup
- Security updates
- Capacity planning review

## Rollback Procedures

### Emergency Rollback

If critical issues occur after deployment:

1. **Stop the bot**:

   ```bash
   sudo systemctl stop trivia-bot
   ```

2. **Restore from backup**:

   ```bash
   python scripts/backup_restore.py restore data/backups/latest_backup.db
   ```

3. **Verify restoration**:

   ```bash
   python scripts/optimize_database.py
   ```

4. **Restart bot**:
   ```bash
   sudo systemctl start trivia-bot
   ```

### Partial Rollback

For schema-only issues:

1. **Identify target backup**:

   ```bash
   python scripts/backup_restore.py list
   ```

2. **Restore specific backup**:
   ```bash
   python scripts/backup_restore.py restore path/to/specific/backup.db
   ```

### Data Recovery

For data corruption:

1. **Run emergency recovery**:

   ```bash
   python scripts/backup_restore.py emergency
   ```

2. **If recovery fails, manual restore**:

   ```bash
   # Find latest valid backup
   python scripts/backup_restore.py list

   # Restore from valid backup
   python scripts/backup_restore.py restore path/to/valid/backup.db
   ```

## Troubleshooting

### Common Issues

1. **Database locked errors**:

   - Check for long-running transactions
   - Verify WAL mode is enabled
   - Restart bot if necessary

2. **Memory issues**:

   - Check connection pool size
   - Monitor cache usage
   - Consider reducing cache size

3. **Backup failures**:
   - Check disk space
   - Verify permissions
   - Check database integrity

### Emergency Contacts

- **System Administrator**: [contact info]
- **Database Administrator**: [contact info]
- **Discord Bot Developer**: [contact info]

### Support Resources

- **Documentation**: `/docs/`
- **Log Files**: `/logs/`
- **Backup Location**: `/data/backups/`
- **Configuration**: `.env` and `logging.conf`

---

**Note**: Always test deployment procedures in a staging environment before applying to production.
