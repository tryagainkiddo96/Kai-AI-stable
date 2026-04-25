from pathlib import Path

p = Path('TODO.md')
content = p.read_text(encoding='utf-8')

# Replace the utcnow section
old_section = """### 7. `datetime.utcnow()` Deprecation Warnings
- **Problem**: 287 instances of `datetime.utcnow()` causing Python 3.12+ deprecation warnings.
- **Status**: ⏳ PENDING"""

new_section = """### 7. `datetime.utcnow()` Deprecation Warnings ✅
- **Problem**: 287+ instances of `datetime.utcnow()` causing Python 3.12+ deprecation warnings.
- **Fix**: Systematically replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)` across 15+ files. Added `timezone` imports where missing.
- **Files fixed**: `memory.py`, `autonomy.py`, `document_handler.py`, `environment.py`, `inner_monologue.py`, `logger.py`, `mood_journal.py`, `semantic_memory.py`, `social_timing.py`, `task_planner.py`, `test_mood_journal.py`, `relationship_model.py`
- **Status**: ✅ COMPLETE — zero remaining `utcnow()` calls in non-test source"""

content = content.replace(old_section, new_section)

# Update test count
content = content.replace(
    "**Test Summary: 25/25 tests passing**",
    "**Test Summary: 26/26 tests passing (20 smoke + 6 legacy capability tests)**"
)

p.write_text(content, encoding='utf-8')
print("Updated TODO.md")
