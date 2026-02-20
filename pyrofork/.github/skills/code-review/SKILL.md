---
name: code-review
description: Comprehensive code review agent for Python Telegram bot. Reviews code before commits, checks syntax, patterns, error handling, logging, and database operations. Use before any code commit or when reviewing pull requests.
---

# Code Review Agent

## Role
Expert code reviewer for Python Telegram bot. Always use before committing code changes.

## Mandatory Rule
**ALWAYS use code review agent before committing any code changes!**

## Review Process

### Step 1: Static Analysis
1. **Check Python syntax**:
   - Use `read_lints` tool to check for syntax errors
   - Verify no `SyntaxError` or `IndentationError`
   - Check indentation consistency (4 spaces)

2. **Check basic errors**:
   - Unclosed brackets, quotes
   - Undefined variables (`NameError`)
   - UnboundLocalError (variable used before assignment in local scope)
   - Unused imports
   - Empty blocks (`try:`, `except:`, `if:`, `for:`, `while:`)
   - **CRITICAL**: Check for `import` statements inside functions that shadow module-level imports
     - If module-level import exists (e.g., `import sys`), don't re-import inside function
     - This causes `UnboundLocalError: cannot access local variable 'X' where it is not associated with a value`

### Step 2: Pattern Compliance
- **Telegram handlers**: Early returns, error handling, async/await
- **Database operations**: Parameterized queries, connection management, transactions
- **Logging**: No PII, appropriate levels, Railway.com-friendly messages
- **Code style**: Follow `systemPatterns.md` conventions

### Step 3: Specific Checks

**Callback handlers**:
- All handlers wrapped in `callback_wrapper`?
- No duplicate `query.answer()` calls?
- Proper error handling?

**Database operations**:
- All SQL queries parameterized (no SQL injection)?
- Proper transaction handling?
- Database migrations safe?

**Logging**:
- No PII in logs?
- Appropriate log levels?
- No Railway.com error keywords in INFO messages?

**Version**:
- Bot version updated?
- Version matches changes?

**Telegram API Integration** (when working with `set_my_commands` or other API calls):
- All commands from `CommandHandler` included in `BotCommand` list? (КРИТИЧНО!)
- Synchronization check performed: all CommandHandler commands are in BotCommand list?
- Verification performed after `set_my_commands()` using `get_my_commands()`?
- Old commands cleared before setting new ones?
- List of commands logged for debugging?
- Errors handled and logged?

## Pre-Commit Checklist

- [ ] Python syntax correct (no `SyntaxError`, `IndentationError`)
- [ ] **NO UnboundLocalError** - check for duplicate imports inside functions
- [ ] **NO shadowing imports** - if module-level import exists, don't re-import in function
- [ ] No empty blocks
- [ ] All variables defined
- [ ] Imports correct (no duplicate imports at function level)
- [ ] Error handling present
- [ ] Logging correct (no PII, appropriate levels)
- [ ] Bot version updated
- [ ] Memory-bank updated
- [ ] Code follows style from `systemPatterns.md`
- [ ] No dead code after `return`
- [ ] Database queries parameterized
- [ ] Async functions use `await` correctly
- [ ] **Telegram API Integration** (if applicable):
  - [ ] **КРИТИЧНО**: All commands from `CommandHandler` included in `BotCommand`?
  - [ ] **КРИТИЧНО**: Synchronization check performed (all CommandHandler commands are in BotCommand)?
  - [ ] Verification performed after `set_my_commands()`?
  - [ ] Old commands cleared before setting new ones?
  - [ ] Commands list logged for debugging?

## Common Errors

### 1. UnboundLocalError (CRITICAL!)
**Symptom**: `UnboundLocalError: cannot access local variable 'sys' where it is not associated with a value`
**Cause**: Importing a module inside a function when it's already imported at module level
**Example**:
```python
import sys  # Module level

def setup_logging():
    _stdout_handler = logging.StreamHandler(sys.stdout)  # Uses sys
    if condition:
        import sys  # ERROR! Shadows module-level import
        print("...", file=sys.stderr)
```
**Solution**: 
- Remove `import sys` from inside function if already imported at module level
- Use module-level import directly: `print("...", file=sys.stderr)`
- Check ALL functions for duplicate imports of modules imported at top level

### 2. IndentationError
**Symptom**: `IndentationError: expected an indented block after 'try' statement`
**Solution**: Ensure all blocks have content or use `pass`

### 3. Duplicate calls
**Symptom**: `query.answer()` called twice
**Solution**: Remove duplicate calls after adding wrapper

### 4. Undefined variables
**Symptom**: `NameError: name 'X' is not defined`
**Solution**: Check order of definition and imports

### 5. Improper error handling
**Symptom**: Errors not logged or handled
**Solution**: Add error handling with logging

## Usage

Always run `read_lints` before committing. Check all items in the checklist. Verify code follows project patterns.
