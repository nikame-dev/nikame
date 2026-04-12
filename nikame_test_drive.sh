#!/bin/bash
set -e

# 🛸 NIKAME v2.0 TEST DRIVE
echo "🛸 Starting NIKAME v2.0 Test Drive..."
# Use absolute path for PYTHONPATH to ensure modules are found even after cd
export PROJECT_ROOT=$(pwd)
export PYTHONPATH=$PROJECT_ROOT:$PYTHONPATH

# 1. RUN CORE TESTS
echo -e "\n[1/4] Running Validation Suite..."
python3 -m pytest --cov=nikame --cov-report=term-missing tests/

# 2. CREATE DEMO PROJECT
echo -e "\n[2/4] Initializing Demo Project (nikame-v2-demo)..."
rm -rf nikame-v2-demo
mkdir nikame-v2-demo
cd nikame-v2-demo

# Use the -m pattern to support relative imports
python3 -m nikame.cli.main init \
    --description "A production-grade demo project" \
    --modules "database.postgres,auth.jwt" \
    nikame-v2-demo

# 3. SCAFFOLD PATTERNS
echo -e "\n[3/4] Injecting Registry Patterns..."
python3 -m nikame.cli.main add database.postgres --registry "$PROJECT_ROOT/registry" -y
python3 -m nikame.cli.main add auth.jwt --registry "$PROJECT_ROOT/registry" -y

# 4. GENERATE INFRASTRUCTURE
echo -e "\n[4/4] Generating Docker Infrastructure..."
python3 -m nikame.cli.main infra docker --path .

echo -e "\n✨ SUCCESS! NIKAME v2.0 has initialized a full project stack."
echo "Project structure:"
ls -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /'

echo -e "\nCheck 'nikame-v2-demo/' for the results."
