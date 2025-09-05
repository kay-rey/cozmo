# Trivia Reaction Troubleshooting Guide

## Issue: Bot Not Responding to Reaction Clicks

If the bot isn't responding when you click on reaction emojis (🇦 🇧 🇨 🇩) during trivia games, follow these steps:

### 1. Quick Fix Applied ✅

I've temporarily switched back to the basic trivia system which has simpler, more reliable reaction handling:

- **Re-enabled**: `cogs/trivia.py` (basic trivia with working reactions)
- **Disabled**: `cogs/enhanced_trivia.py` (complex system with initialization issues)

### 2. Test the Fix

1. **Restart your bot** (redeploy on Render)
2. **Try a trivia game**: `!trivia`
3. **Click on a reaction** (🇦 🇧 🇨 🇩)
4. **Check if bot responds** with correct/incorrect message

### 3. Debug Commands (Admin Only)

If reactions still don't work, use these admin commands:

```
!triviadebug    # Shows active games and bot permissions
!checkperms     # Shows detailed permission status
```

### 4. Common Causes & Solutions

#### **Bot Permissions Missing**

- **Required**: Add Reactions, Manage Messages, Send Messages
- **Fix**: Grant permissions in Discord server settings

#### **Bot Not Seeing Reactions**

- **Cause**: Discord API issues or bot restart needed
- **Fix**: Restart bot, check bot is online

#### **Wrong Message/Channel**

- **Cause**: Multiple trivia games or old messages
- **Fix**: Only one trivia game per channel, use fresh `!trivia` command

#### **Emoji Issues**

- **Cause**: Custom emojis or wrong emoji format
- **Fix**: Bot uses standard flag emojis (🇦 🇧 🇨 🇩)

### 5. What Changed

**Before (Enhanced System)**:

```
!trivia → Enhanced Trivia Cog → Game Manager → Complex Processing
```

**Now (Basic System)**:

```
!trivia → Basic Trivia Cog → Direct Reaction Handler → Immediate Response
```

### 6. Expected Behavior

When working correctly:

1. **Start game**: `!trivia`
2. **Bot posts question** with 🇦 🇧 🇨 🇩 reactions
3. **Click reaction**: Bot immediately responds
4. **Bot shows result**: "🎉 Correct!" or "❌ Incorrect!"
5. **Reactions cleared**: Bot removes all reactions

### 7. Logs to Check

Look for these log messages:

```
✅ Good: "Reaction detected: 🇦 by Username in channel 123456"
✅ Good: "Active game found, expected message ID: 789, got: 789"
✅ Good: "User Username answered trivia correctly in channel 123456"

❌ Bad: "No active game in channel 123456"
❌ Bad: "Message ID mismatch - ignoring reaction"
❌ Bad: "Missing permissions to send messages in trivia channel"
```

### 8. Next Steps

Once basic reactions are working:

1. **Debug enhanced system**: Fix GameManager initialization
2. **Gradual migration**: Move features one by one
3. **Test thoroughly**: Ensure no regressions

### 9. Emergency Rollback

If issues persist, you can always rollback to the last working state by reverting the cog changes.

## Contact

If reactions still don't work after these steps, the issue might be:

- Discord API problems
- Bot hosting issues
- Network connectivity problems
- Discord server-specific settings

Check Discord status and bot hosting platform status first.
