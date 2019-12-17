"""
Non-interactive tests.
"""
import os
import subprocess
import pytest
from mssqltestutils import (
    create_mssql_cli,
    random_str,
    shutdown,
    test_queries,
    get_file_contents,
    get_io_paths,
    _BASELINE_DIR
)


class TestNonInteractiveResults:
    """
    Tests non-interactive features.
    """
    @staticmethod
    @pytest.fixture()
    def tmp_filepath():
        """ pytest fixture which returns filepath string and removes the file after tests
        complete. """
        fp = os.path.join(_BASELINE_DIR, "test_query_baseline", "%s.txt" % random_str())
        yield fp
        os.remove(fp)

    @pytest.mark.parametrize("query_str, test_file", test_queries)
    @pytest.mark.timeout(60)
    def test_query(self, query_str, test_file):
        """ Tests query outputs to command-line, ensuring -Q and -i produce
        the same results. """
        file_input, file_baseline = get_io_paths(test_file)
        output_baseline = get_file_contents(file_baseline)

        # test with -Q
        output_query_for_Q = self.execute_query_via_subprocess(query_str)
        assert output_query_for_Q == output_baseline

        # test with -i
        output_query_for_i = self.execute_query_via_subprocess("-i %s" % file_input)
        assert output_query_for_i == output_baseline

    @pytest.mark.parametrize("query_str, test_file", test_queries)
    @pytest.mark.timeout(60)
    def test_output_file(self, query_str, test_file, tmp_filepath):
        """ Tests -o (and ensures file overwrite works) """
        file_input, file_baseline = get_io_paths(test_file)
        output_baseline = get_file_contents(file_baseline)

        # test with -Q
        output_query_for_Q = self.execute_query_via_subprocess(query_str, output_file=tmp_filepath)
        assert output_query_for_Q == output_baseline

        # test with -i
        output_query_for_i = self.execute_query_via_subprocess("-i %s" % file_input,
                                                               output_file=tmp_filepath)
        assert output_query_for_i == output_baseline

    @pytest.mark.timeout(60)
    def test_long_query(self, tmp_filepath):
        """ Output large query using Python class instance. """
        query_str = "SELECT * FROM STRING_SPLIT(REPLICATE(CAST('X,' AS VARCHAR(MAX)), 1024), ',')"
        try:
            mssqlcli = create_mssql_cli(interactive_mode=False, output_file=tmp_filepath)
            output_query = '\n'.join(mssqlcli.execute_query(query_str))
            file_baseline = get_io_paths('big.txt')[1]
            output_baseline = get_file_contents(file_baseline)
            assert output_query == output_baseline

            # test output to file
            output_query_from_file = get_file_contents(tmp_filepath)
            assert output_query_from_file == output_baseline
        finally:
            shutdown(mssqlcli)

    @staticmethod
    @pytest.mark.timeout(60)
    def test_noninteractive_run():
        """ Test that calling run throws an exception only when interactive_mode is false """
        mssqlcli = create_mssql_cli(interactive_mode=False)
        try:
            mssqlcli.run()
            assert False
        except ValueError:
            assert True
        finally:
            shutdown(mssqlcli)

    @classmethod
    @pytest.mark.timeout(60)
    def test_Q_with_i_run(cls):
        """ Tests failure of using -Q with -i """
        output = cls.execute_query_via_subprocess("-Q 'select 1' -i 'this_breaks.txt'")
        assert output == "Invalid arguments: either -Q or -i may be specified."

    @classmethod
    def execute_query_via_subprocess(cls, query_str, output_file=None):
        """ Helper method for running a query. """
        cli_call = os.path.join(".", "mssql-cli %s" % query_str)
        if output_file is not None:
            cli_call += " -o %s" % output_file
        p = subprocess.Popen(cli_call, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        output, errs = p.communicate()
        if errs:
            print(errs)

        if output_file:
            # get file contents if we used -o
            return get_file_contents(output_file)
        return output.decode("utf-8").replace('\r', '').strip()


class TestNonInteractiveShutdownQuery:
    """
    Ensures that client session has shut down after mssql-cli runs in non-interactive mode.
    """
    @staticmethod
    @pytest.fixture(scope='function')
    def mssqlcli():
        """ Create new mssql-cli instance for each test """
        return create_mssql_cli(interactive_mode=False)

    testdata = [
        "select 1",
        "gibberish"
    ]

    @staticmethod
    @pytest.mark.parametrize("query_str", testdata)
    @pytest.mark.timeout(60)
    def test_shutdown_after_query(query_str, mssqlcli):
        """ Runs unit tests on process closure given a query string. """
        print()
        try:
            mssqlcli.execute_query(query_str)
        finally:
            shutdown(mssqlcli)
            assert mssqlcli.mssqlcliclient_main.sql_tools_client.\
                tools_service_process.poll() is not None


class TestNonInteractiveShutdownOutput:
    """
    Ensures that client session has shut down after mssql-cli runs in non-interactive mode,
    with -o enabled.
    """
    @staticmethod
    @pytest.fixture(scope='function')
    def mssqlcli():
        """ Create new mssql-cli instance for each test """
        output_file = os.path.join(_BASELINE_DIR, 'tmp.txt')
        yield create_mssql_cli(interactive_mode=False, output_file=output_file)
        os.remove(output_file)

    testdata = [
        "select 1",
        "gibberish"
    ]

    @staticmethod
    @pytest.mark.parametrize("query_str", testdata)
    @pytest.mark.timeout(60)
    def test_shutdown_after_query(query_str, mssqlcli):
        """ Runs unit tests on process closure given a query string. """
        print()
        try:
            mssqlcli.execute_query(query_str)
        finally:
            shutdown(mssqlcli)
            assert mssqlcli.mssqlcliclient_main.sql_tools_client.\
                tools_service_process.poll() is not None
