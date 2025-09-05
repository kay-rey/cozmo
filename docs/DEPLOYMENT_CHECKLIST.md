# Deployment Checklist

Use this checklist to ensure a successful deployment of the Enhanced Trivia System.

## Pre-Deployment Phase

### Environment Preparation

- [ ] Production server meets system requirements
- [ ] Python 3.8+ installed and configured
- [ ] Virtual environment created and activated
- [ ] All dependencies installed from requirements.txt
- [ ] Discord bot token obtained and secured
- [ ] Environment variables configured (use config/production.env.template)
- [ ] Data directories created (data/, data/backups/, logs/)
- [ ] File permissions set correctly (600 for .env, 755 for scripts)

### Code Preparation

- [ ] Latest code pulled from repository
- [ ] Configuration files updated for production
- [ ] Logging configuration set to appropriate level
- [ ] Debug mode disabled
- [ ] All tests passing
- [ ] Code review completed

### Database Preparation

- [ ] Current database backed up
- [ ] Database integrity verified
- [ ] Migration scripts tested in staging
- [ ] Rollback procedures documented and tested

## Deployment Phase

### Pre-Migration Steps

- [ ] **CRITICAL**: Create pre-deployment backup
  ```bash
  python scripts/backup_restore.py backup --type pre_deployment
  ```
- [ ] Stop existing bot instance (if upgrading)
  ```bash
  sudo systemctl stop trivia-bot
  ```
- [ ] Verify database integrity
  ```bash
  python scripts/optimize_database.py
  ```
- [ ] Check current schema version
  ```bash
  sqlite3 data/trivia.db "SELECT MAX(version) FROM schema_version;"
  ```

### Migration Execution

- [ ] Run database migration
  ```bash
  python scripts/migrate_database.py
  ```
- [ ] Verify migration success (check logs for errors)
- [ ] Confirm schema version updated
- [ ] Run post-migration integrity check

### Database Optimization

- [ ] Optimize database performance
  ```bash
  python scripts/optimize_database.py
  ```
- [ ] Update database statistics
- [ ] Create optimized indexes
- [ ] Vacuum database if needed (high fragmentation)

### Application Deployment

- [ ] Update application configuration
- [ ] Set production environment variables
- [ ] Configure logging for production
- [ ] Set up systemd service (Linux) or equivalent
- [ ] Start bot service
  ```bash
  sudo systemctl start trivia-bot
  ```
- [ ] Verify bot starts successfully
- [ ] Check initial log entries for errors

## Post-Deployment Phase

### Verification Tests

- [ ] Run comprehensive health check
  ```bash
  python scripts/health_check.py
  ```
- [ ] Test basic bot functionality
  - [ ] Bot responds to ping
  - [ ] Help command works
  - [ ] Question command works
  - [ ] Leaderboard displays correctly
- [ ] Verify database operations
  - [ ] User registration works
  - [ ] Score tracking functions
  - [ ] Achievements unlock properly
- [ ] Test error handling
  - [ ] Invalid commands handled gracefully
  - [ ] Database errors logged properly
  - [ ] Recovery mechanisms function

### Backup Verification

- [ ] Create post-deployment backup
  ```bash
  python scripts/backup_restore.py backup --type post_deployment
  ```
- [ ] Verify backup integrity
- [ ] Test backup restoration process (in staging)
- [ ] Confirm automated backup scheduling works

### Monitoring Setup

- [ ] Configure log monitoring
- [ ] Set up health check automation
  ```bash
  # Add to crontab for regular health checks
  */15 * * * * /path/to/scripts/health_check.py
  ```
- [ ] Configure alerting for critical issues
- [ ] Verify performance monitoring
- [ ] Set up disk space monitoring

### Documentation Updates

- [ ] Update deployment documentation
- [ ] Record deployment timestamp and version
- [ ] Document any configuration changes
- [ ] Update runbook with new procedures

## Rollback Procedures (If Needed)

### Emergency Rollback

If critical issues are discovered:

- [ ] Stop the bot immediately
  ```bash
  sudo systemctl stop trivia-bot
  ```
- [ ] Restore from pre-deployment backup
  ```bash
  python scripts/backup_restore.py restore data/backups/pre_deployment_backup.db
  ```
- [ ] Verify restoration
  ```bash
  python scripts/health_check.py
  ```
- [ ] Restart with previous version
- [ ] Document issues for investigation

### Partial Rollback

For non-critical issues:

- [ ] Identify specific problem area
- [ ] Create current state backup
- [ ] Apply targeted fix or restore specific component
- [ ] Test fix thoroughly
- [ ] Monitor for additional issues

## Sign-off

### Technical Sign-off

- [ ] Database migration completed successfully
- [ ] All health checks passing
- [ ] Performance within acceptable limits
- [ ] Backup and recovery tested
- [ ] Monitoring and alerting active

**Technical Lead**: ********\_******** Date: ****\_****

### Functional Sign-off

- [ ] All core features working
- [ ] User experience unchanged or improved
- [ ] No data loss detected
- [ ] Performance acceptable to users

**Product Owner**: ********\_******** Date: ****\_****

### Operations Sign-off

- [ ] Monitoring configured and active
- [ ] Backup procedures verified
- [ ] Runbook updated
- [ ] Support team briefed

**Operations Lead**: ********\_******** Date: ****\_****

## Post-Deployment Monitoring

### First 24 Hours

- [ ] Monitor error rates closely
- [ ] Check performance metrics
- [ ] Verify backup creation
- [ ] Monitor user feedback
- [ ] Watch for memory leaks or resource issues

### First Week

- [ ] Review weekly performance trends
- [ ] Analyze user engagement metrics
- [ ] Check backup retention and cleanup
- [ ] Review and tune monitoring thresholds
- [ ] Gather user feedback

### First Month

- [ ] Conduct performance review
- [ ] Analyze capacity requirements
- [ ] Review and update documentation
- [ ] Plan next iteration improvements
- [ ] Conduct lessons learned session

## Emergency Contacts

**Primary On-Call**: [Name] - [Phone] - [Email]
**Secondary On-Call**: [Name] - [Phone] - [Email]
**Database Admin**: [Name] - [Phone] - [Email]
**Infrastructure Team**: [Name] - [Phone] - [Email]

## Important Commands Reference

```bash
# Health check
python scripts/health_check.py

# Create backup
python scripts/backup_restore.py backup --type manual

# List backups
python scripts/backup_restore.py list

# Restore backup
python scripts/backup_restore.py restore path/to/backup.db

# Database optimization
python scripts/optimize_database.py

# Migration
python scripts/migrate_database.py

# Service management (Linux)
sudo systemctl status trivia-bot
sudo systemctl start trivia-bot
sudo systemctl stop trivia-bot
sudo systemctl restart trivia-bot

# View logs
tail -f logs/trivia_bot.log
journalctl -u trivia-bot -f
```

---

**Remember**: Always test deployment procedures in staging before production!
