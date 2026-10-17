# Generate hash-pinned lockfiles with pip-tools (needs network). Commit the results.
#   .\scripts\lock_dependencies.ps1
$ErrorActionPreference = "Stop"
python -m pip install "pip-tools>=7.4,<8.0"
pip-compile --generate-hashes --output-file requirements.lock pyproject.toml
pip-compile --generate-hashes --extra dev --output-file requirements-dev.lock pyproject.toml
Write-Host "Wrote requirements.lock and requirements-dev.lock"
