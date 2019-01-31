import shutil

import pytest

from rampdb.model import Model
from rampdb.testing import add_users
from rampdb.tools.team import sign_up_team
from rampdb.tools.submission import get_submissions
from rampdb.tools.submission import submit_starting_kits
from rampdb.utils import session_scope
from rampdb.utils import setup_db

from rampdb.tools.event import get_problem

from rampbkd.local import CondaEnvWorker
from rampbkd.dispatcher import Dispatcher

from ramputils import generate_ramp_config
from ramputils import read_config
from ramputils.testing import path_config_example

from ramputils.deploy import deploy_ramp_event


@pytest.fixture(scope='module')
def config():
    return read_config(path_config_example())


@pytest.fixture
def session_scope_function(config):
    try:
        yield
    finally:
        shutil.rmtree(config['ramp']['deployment_dir'], ignore_errors=True)
        db, _ = setup_db(config['sqlalchemy'])
        Model.metadata.drop_all(db)


def test_deploy_ramp_event_options(session_scope_function):
    config_file = path_config_example()
    config = read_config(config_file)
    ramp_config = generate_ramp_config(config_file)
    deploy_ramp_event(config_file)
    # deploy again by forcing the deployment
    deploy_ramp_event(config_file, force=True)
    # do not deploy the kit to trigger the error in the problem with we don't
    # force the deployment
    msg_err = 'The RAMP problem already exists in the database.'
    with pytest.raises(ValueError, match=msg_err):
        with session_scope(config['sqlalchemy']) as session:
            problem = get_problem(session, 'iris')
            problem.path_ramp_kits = problem.path_ramp_kits + '_xxx'
            session.commit()
            deploy_ramp_event(config_file, setup_ramp_repo=False, force=False)

            problem = get_problem(session, 'iris')
            problem.path_ramp_kits = ramp_config['ramp_kits_dir']
            problem.path_ramp_data = problem.path_ramp_data + '_xxx'
            session.commit()
            deploy_ramp_event(config_file, setup_ramp_repo=False, force=False)


def test_deploy_ramp_event(session_scope_function):
    config_file = path_config_example()
    config = read_config(config_file)
    ramp_config = generate_ramp_config(config_file)
    deploy_ramp_event(config_file)

    # simulate that we add users and sign-up for the event and that they
    # submitted the starting kit
    with session_scope(config['sqlalchemy']) as session:
        add_users(session)
        sign_up_team(session, ramp_config['event_name'], 'test_user')
        submit_starting_kits(session, ramp_config['event_name'], 'test_user',
                             ramp_config['ramp_kit_submissions_dir'])

    # run the dispatcher on the event which are in the dataset
    dispatcher = Dispatcher(config=config,
                            worker=CondaEnvWorker, n_worker=-1,
                            hunger_policy='exit')
    dispatcher.launch()

    # the iris kit contain a submission which should fail for a user
    with session_scope(config['sqlalchemy']) as session:
        submission = get_submissions(session, config['ramp']['event_name'],
                                     'training_error')
        assert len(submission) == 1
