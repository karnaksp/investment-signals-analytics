import pytest

from dbt_af.common.constants import OTHER_DBT_CLI_OPTIONS, OTHER_DBT_CLI_OPTIONS_DEFAULT
from dbt_af.common.utils import build_dbt_run_model_bash_extra_options


@pytest.mark.parametrize(
    'other_dbt_cli_options',
    [
        None,
        {},
        OTHER_DBT_CLI_OPTIONS_DEFAULT,
    ],
)
def test_build_dbt_run_model_bash_extra_options_ignores_empty_and_default_other_options(other_dbt_cli_options):
    bash_options, bash_flags = build_dbt_run_model_bash_extra_options(
        {
            OTHER_DBT_CLI_OPTIONS: other_dbt_cli_options,
        }
    )

    assert bash_options == {}
    assert bash_flags == set()


def test_build_dbt_run_model_bash_extra_options_keeps_custom_other_options():
    bash_options, bash_flags = build_dbt_run_model_bash_extra_options(
        {
            OTHER_DBT_CLI_OPTIONS: {
                '--option': 'custom-value',
                'profiles-dir': '/tmp/profiles',
            },
        }
    )

    assert bash_options == {
        '--option': 'custom-value',
        '--profiles-dir': '/tmp/profiles',
    }
    assert bash_flags == set()
