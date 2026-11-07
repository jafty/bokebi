#!/bin/sh
# Run from the repository root after installing requirements-dev.txt.
set -eu
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m coverage run --branch --source=domain -m pytest tests/test_domain.py -q
python -m coverage report -m --fail-under=100
# mutmut caches test-to-function mappings. Rebuild them for an honest fresh run.
rm -rf mutants
mutmut run --max-children 2
results=$(mutmut results)
if [ -n "$results" ]; then
    printf '%s\n' "$results"
    exit 1
fi
printf '%s\n' 'All generated mutants were killed.'
