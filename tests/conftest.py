import warnings

# Silence noisy Strawberry extension deprecation warning that appears during async execution.
warnings.filterwarnings(
    "ignore",
    message="Event driven styled extensions for on_request_start or on_request_end are deprecated",
    category=DeprecationWarning,
)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Emit a concise list of passed tests so the outcome is visible
    even without verbose flags.
    """
    passed = terminalreporter.stats.get("passed", [])
    if not passed:
        return

    terminalreporter.write_sep("-", "Passed tests")
    for rep in passed:
        terminalreporter.write_line(rep.nodeid)
