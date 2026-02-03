# Question Generation Workflow Improvements

## Overview
This document describes the improved workflow designed to achieve at least 30% pass rate in question validation.

## Key Changes

### 1. Enhanced GENERATE Prompt
**Focus: Self-Containment**
- Emphasizes including ALL necessary information in the question stem
- Provides explicit template: "When [material/system] exhibits [specific observation], under [stated conditions], what is the most likely explanation?"
- Includes concrete examples of good vs bad questions
- Adds self-check checklist before finalizing

**Key Improvements:**
- Questions must state specific materials, conditions, measurements explicitly
- Avoids requiring "what the paper found" knowledge
- Ensures domain experts can answer with only question text + general knowledge

### 2. Improved REVISE Prompt
**Focus: Option Quality**
- Prioritizes question-dependent options (avoid universally true/false statements)
- Explicit anti-redundancy rules with examples
- Distribution strategy for 6 new options
- Self-check for distinctness and plausibility

**Key Improvements:**
- Each option must require question context to evaluate
- No paraphrases or near-synonyms
- Options reference specific aspects from question stem

### 3. New CRITIQUE Step
**Purpose: Pre-validation Quality Control**
- Inserted between generation and expansion phases
- Checks for self-containment, option independence, redundancy, correctness
- Fixes issues before expanding to 10 options
- Reduces wasted effort on flawed questions

**Benefits:**
- Catches common failures early
- Improves base question quality before expansion
- Reduces validation failures

### 4. Trial Management System
**Features:**
- Tracks up to 10 trials automatically
- Records pass rates and drop reasons
- Identifies best result
- Stops when 30% target achieved or max trials reached

## Workflow Pipeline

```
Paper Structure
    ↓
[GENERATE] - Create 3 questions with 4 options
    ↓
[CRITIQUE] - Self-check and fix issues
    ↓
[REWRITE] - Expand to 10 options
    ↓
[VALIDATE] - Run validation pipeline
    ↓
Results + Drop Reason Analysis
```

## Expected Improvements

### Primary Failure Modes Addressed:
1. **Not self-contained** → Enhanced GENERATE prompt with explicit instructions
2. **Options independent of question** → Improved REVISE prompt with dependency rules
3. **Redundant options** → CRITIQUE step + anti-redundancy rules
4. **Answer K (unanswerable)** → Better question construction template
5. **Too many independent options** → Option quality focus in REVISE

### Target Metrics:
- Pass rate: ≥30%
- Questions generated: ~3 per paper
- Valid questions: ≥30% of generated

## Validation Criteria (Unchanged)
1. Self-contained (no paper-specific details required)
2. Not self-contradictory
3. No redundant information
4. Plausible assumptions
5. Options depend on question context
6. Correct answer is not K
7. No trivially true/false options
8. No redundant options
