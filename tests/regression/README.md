# Regression Tests

## 🎯 Purpose

Regression tests prevent previously fixed bugs from recurring and establish behavioral baselines for refactoring validation.

## 📁 Test Files

### **test_behavioral_baseline.py** (Compression Baseline)
**Purpose:** Establish baseline for compression output behavior before/after major refactoring
**Usage:** Run before and after system/ops refactoring
**Tests:** 8 tests (4 baseline + 4 regression)
**Focus:** Actual compression output, file hashes, size comparisons

### **test_subprocess_refactoring.py** (Subprocess Refactoring)
**Purpose:** Validate subprocess refactoring preserves behavioral correctness
**Status:** ✅ Complete - All tests pass
**Tests:** Behavioral tests for subprocess operations
**Focus:** Observable behavior (console hiding, timeouts, errors) vs implementation details

---

## 🧪 Running Tests

### **All regression tests:**
```bash
pytest tests/regression/ -v
```

### **Specific test suites:**
```bash
# Compression baseline tests
pytest tests/regression/test_behavioral_baseline.py -v

# Subprocess refactoring tests
pytest tests/regression/test_subprocess_refactoring.py -v
```

---

## 📋 Test Organization

### **Compression Baseline Tests**
- **When to use:** Before/after major compression algorithm changes
- **What they test:** Actual compression output, file hashes, size validation
- **How they work:** Run real compression, compare before/after results

### **Subprocess Refactoring Tests**
- **When to use:** After subprocess handling changes
- **What they test:** Observable subprocess behavior (no popups, errors, timeouts)
- **How they work:** Test actual subprocess calls and error handling
- **Focus:** User-facing behavior rather than low-level properties

---

## 🎯 Philosophy

### **Behavioral > Implementation**
Our tests focus on **observable behavior** rather than implementation details:

✅ **Tests behavior:**
- Console windows don't appear on Windows
- Timeouts raise helpful errors
- File verification catches missing files
- Error messages are actionable

❌ **Avoids testing:**
- Specific internal flag values
- Implementation method signatures
- Low-level property checks

### **Why Behavioral Tests?**
- **More robust** - Don't break when implementation changes
- **Better validation** - Test what users actually experience
- **Future-proof** - Survive refactoring and optimization
- **User-focused** - Verify what actually matters to users

---

## 📊 Test Coverage

| Test Suite | Purpose | Behavioral Focus | Runtime |
|------------|---------|-------------------|----------|
| **Compression Baseline** | Output validation | File hashes, sizes | ~30s (with binaries) |
| **Subprocess Refactoring** | Operation validation | No popups, errors, timeouts | ~5s |

---

## 🚀 Adding New Regression Tests

When fixing bugs or refactoring:

### **1. Bug Fix (Regression Prevention)**
1. Reproduce the bug
2. Write test that catches it
3. Fix the bug
4. Verify test passes
5. Keep test to prevent regression

### **2. Major Refactoring (Baseline Validation)**
1. Run baseline tests BEFORE refactoring
2. Save baseline results
3. Perform refactoring
4. Run same tests AFTER refactoring
5. Compare results - should match baseline

---

## 🔍 Test Maintenance

### **When to update tests:**
- **Keep:** Tests that prevent real bugs
- **Update:** Tests that are too brittle or implementation-specific
- **Remove:** Tests that no longer serve a purpose

### **Red flags to avoid:**
- ❌ Testing implementation details instead of behavior
- ❌ Over-mocking that makes tests fragile
- ❌ Tests that break with every refactoring
- ❌ Tests that are harder to maintain than the code

### **Good test patterns:**
- ✅ Test user-facing behavior
- ✅ Test error conditions
- ✅ Test cross-platform compatibility
- ✅ Test observable outcomes
- ✅ Tests that catch real regressions

---

## 📈 Success Metrics

**Good regression tests should:**
- ✅ Catch real bugs that users would experience
- ✅ Survive legitimate refactoring
- ✅ Run quickly (< 1 minute total)
- ✅ Be easy to understand and maintain
- ✅ Document what they're protecting against

---

**The goal is preventing regressions while staying out of the way of legitimate improvements!**