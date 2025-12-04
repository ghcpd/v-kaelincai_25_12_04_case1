# Run legacy tests and greenfield tests and produce a simple JSON summary
python -m pytest c:\workspace\issue_project -q --disable-warnings || exit 1
python -m pytest . -q --disable-warnings || exit 1
