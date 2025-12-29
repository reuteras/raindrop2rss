"""NOX testing harness."""

import nox

PYTHON_VERSIONS = [
    # Most up-to-date patch versions of each major version we support.
    "3.10.14",
    "3.11.9",
    "3.12.3",
]


@nox.session(python=PYTHON_VERSIONS)
def api_test_suite(session):
    """Run all our pytest suite."""
    # Export our package requirements from Poetry to requirements.txt (temporarily):
    session.run("poetry", "export", "--format=requirements.txt", "--output=requirements.txt", external=True)

    # Install packages into our .nox venv environment (pytest is already included as we're taking 'dev' packages)
    session.run("poetry", "install", external=True)

    # Run our actual test suite..
    session.run("pytest")

    # Cleanup (explicitly use `/bin/rm` to avoid our fish alias of `rm` to `rip`)
    session.run("/bin/rm", "-f", "requirements.txt", external=True)
