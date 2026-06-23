*** Settings ***
Library    okw_env.library.OkwEnvLibrary    components_dir=components    WITH NAME    ENV

*** Test Cases ***
Database Is Reachable
    [Documentation]    Start a PostgresDB container and verify it becomes ready.
    ENV_Start        PostgresDB
    ENV_BuildAndRun
    ENV_WaitForReady    PostgresDB    timeout=30s
    Log    PostgresDB is ready for testing.
    [Teardown]    ENV_Stop

Database And Cache Together
    [Documentation]    Start multiple components in one test.
    ENV_Start        PostgresDB
    ENV_Start        Redis
    ENV_BuildAndRun
    ENV_WaitForReady    PostgresDB    timeout=30s
    ENV_WaitForReady    Redis         timeout=10s
    Log    Both services are running.
    [Teardown]    Run Keywords    ENV_SnapshotOnFail    ENV_Stop
