import os
import logging
import numpy as np
import pandas as pd
#import fabric.contrib.project as project
from fabric.api import *
from fabric.contrib.files import exists
from databoard.model import shelve_database, ModelState
import databoard.config_databoard as config_databoard

# for pickling theano
import sys
sys.setrecursionlimit(50000)

# Open ports in Stratuslab
# 22, 80, 389, 443, 636, 2135, 2170, 2171, 2172, 2811, 3147, 5001, 5010, 5015, 
# 8080, 8081, 8095, 8188, 8443, 8444, 9002, 10339, 10636, 15000, 15001, 15002, 
# 15003, 15004, 20000-25000.

# the user to use for the remote commands
#env.user = config_databoard.get_ramp_field('deploy_user') 
#env.use_ssh_config = True

# the servers where the commands are executed
#env.hosts = [config_databoard.get_ramp_field('train_user') + '@' + config_databoard.get_ramp_field('train_server'), 
#             config_databoard.get_ramp_field('web_user') + '@' + config_databoard.get_ramp_field('web_server'),]

#production = env.hosts[0]
logger = logging.getLogger('databoard')


def clear_cache():
    from sklearn.externals.joblib import Memory

    logger.info('Flushing the joblib cache.')
    mem = Memory(cachedir=config_databoard.cachedir)
    mem.clear()


def clear_db():
    from databoard.model import columns

    logger.info('Clearing the database.')
    with shelve_database('c') as db:
        db.clear()
        db['models'] = pd.DataFrame(columns=columns)
        db['leaderboard1'] = pd.DataFrame(columns=['score'])
        db['leaderboard2'] = pd.DataFrame(columns=['contributivity'])


def clear_registrants():
    import shutil
    # Prepare the teams repo submodules
    # logger.info('Init team repos git')
    # repo = Repo.init(config_databoard.repos_path)  # does nothing if already exists

    # Remove the git repos of the teams
    logger.info('Clearing the teams repositories.')
    shutil.rmtree(config_databoard.repos_path, ignore_errors=True)
    os.mkdir(config_databoard.repos_path)

    logger.info('Clearing the models directory.')
    shutil.rmtree(config_databoard.models_path, ignore_errors=True)
    os.mkdir(config_databoard.models_path)
    open(os.path.join(config_databoard.models_path, '__init__.py'), 'a').close()


def clear_pred_files():
    import glob
    fnames = glob.glob(
        os.path.join(config_databoard.models_path, '*', '*', '*', '*.csv'))

    for fname in fnames:
        if os.path.exists(fname):
            logger.info("Removing {}".format(fname))
            os.remove(fname)


def clear_groundtruth():
    import shutil    
    shutil.rmtree(config_databoard.ground_truth_path, ignore_errors=True)
    os.mkdir(config_databoard.ground_truth_path)


def setup_ground_truth():
    from databoard.generic import setup_ground_truth
    from databoard.specific import prepare_data

    # Preparing the data set, typically public train/private held-out test cut
    logger.info('Preparing the dataset.')
    prepare_data()

    logger.info('Removing the ground truth files.')
    clear_groundtruth()

    # Set up the ground truth predictions for the CV folds
    logger.info('Setting up the groundtruth.')
    setup_ground_truth()


def setup():
    setup_ground_truth()
    clear_db()
    clear_registrants()
    # Flush joblib cache
    clear_cache()
    # todo: set up database


def print_db(table='models', state=None):
    with shelve_database('c') as db:
        if table not in db:
            print('Select one of the following tables:')
            print '\n'.join('\t- {}'.format(t) for t in db)
            return
        df = db[table]
    pd.set_option('display.max_rows', len(df))
    if not state:
        print df
    else:
        print df[df.state == state]


def fetch():
    from databoard.fetch import fetch_models
    fetch_models()


def repeat_fetch(delay='60'):
    import time
    while True:
        fetch()
        delay = int(os.getenv('FETCH_DELAY', delay))
        time.sleep(delay)


def leaderboard(which='all', test=False, calibrate=False):
    from databoard.leaderboard import (
        leaderboard_classical,
        leaderboard_combination,
        leaderboard_execution_times,
    )

    with shelve_database() as db:
        submissions = db['models']
        trained_models = submissions[
            np.any([submissions['state'] == "test_error",
                    submissions['state'] == "trained",
                    submissions['state'] == "tested"], axis=0)]
        tested_models = submissions[submissions['state'] == "tested"]
        pd.set_option('display.max_rows', len(trained_models))
        print trained_models

    if which in ('all', 'classical'):
        l1 = leaderboard_classical(trained_models, calibrate=calibrate)
        # The following assignments only work because leaderboard_classical & co
        # are idempotent.
        # FIXME (potentially)
        with shelve_database() as db:
            db['leaderboard1'] = l1
            if test:
                l_test = leaderboard_classical(
                    tested_models, subdir="test", calibrate=calibrate)
                db['leaderboard_classical_test'] = l_test

    if which in ('all', 'combined'):
        l2 = leaderboard_combination(trained_models, test)
        # FIXME: same as above
        with shelve_database() as db:
            db['leaderboard2'] = l2

    if which in ('all', 'times'):
        l_times = leaderboard_execution_times(trained_models)
        # FIXME: same as above
        with shelve_database() as db:
            db['leaderboard_execution_times'] = l_times


def check(state=False, tag=None, team=None):
    from databoard.train_test import check_models

    with shelve_database() as db:
        models = db['models']

    if tag is not None:
        models = models[models.model == tag]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the tag: {}'.format(tag))
            return

    if team is not None:
        models = models[models.team == team]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the team: {}'.format(tag))
            return

    if not state:
        state = 'new'

    if state != 'all': 
        models = models[models.state == state]

    check_models(models)

    idx = models.index

    with shelve_database() as db:
        db['models'].loc[idx, :] = models


def train(state=False, tag=None, team=None):
    from databoard.train_test import train_and_valid_models

    with shelve_database() as db:
        models = db['models']

    if tag is not None:
        models = models[models.model == tag]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the tag: {}'.format(tag))
            return

    if team is not None:
        models = models[models.team == team]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the team: {}'.format(tag))
            return

    if not state:
        state = 'new'

    if state != 'all': 
        models = models[models.state == state]

    train_and_valid_models(models)

    idx = models.index

    with shelve_database() as db:
        db['models'].loc[idx, :] = models


def test(state=False, tag=None, team=None):
    from databoard.train_test import test_models

    with shelve_database() as db:
        models = db['models']

    if tag is not None:
        models = models[models.model == tag]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the tag: {}'.format(tag))
            return

    if team is not None:
        models = models[models.team == team]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the team: {}'.format(tag))
            return

    if not state:
        state = 'trained'

    if state != 'all':
        models = models[models.state == state]

    test_models(models)

    idx = models.index

    with shelve_database() as db:
        db['models'].loc[idx, :] = models


def train_test(state=False, tag=None, team=None):
    from databoard.train_test import train_valid_and_test_models

    with shelve_database() as db:
        models = db['models']

    if tag is not None:
        models = models[models.model == tag]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the tag: {}'.format(tag))
            return

    if team is not None:
        models = models[models.team == team]
        state = 'all'  # force train all the selected models
        if len(models) == 0:
            print('No existing model with the team: {}'.format(tag))
            return

    if not state:
        state = 'new'
    
    if state != 'all': 
        models = models[models.state == state]

    train_valid_and_test_models(models)

    idx = models.index

    with shelve_database() as db:
        db['models'].loc[idx, :] = models


def change_state(from_state, to_state):
    with shelve_database() as db:
        models = db['models']
    models = models[models['state'] == from_state]

    idx = models.index
    with shelve_database() as db:
        db['models'].loc[idx, 'state'] = to_state


def set_state(team, tag, state):
    with shelve_database() as db:
        models = db['models']
    models = models[np.logical_and(models['model'] == tag, 
                                   models['team'] == team)]

    if len(models) > 1:
        print "ambiguous selection"
        print selected_models
        return
    if len(models) == 0:
        print "no model found"
        return
    idx = models.index
    with shelve_database() as db:
        db['models'].loc[idx, 'state'] = state


def kill(team, tag):
    import glob
    import signal
    from databoard.fetch import get_tag_uid

    answer = 'y'
    while answer != 'y':
        answer = raw_input('Sure? (y/n): ')

    pid_filenames = os.path.join(
        config_databoard.models_path, team, get_tag_uid(team, tag), 'pid_*')
    print pid_filenames
    for f in glob.glob(pid_filenames):
        with open(f) as pid_file:
            pid = pid_file.read()
            os.kill(int(pid), signal.SIGKILL)


def serve(port=None):
    from databoard import app
    if port is None:
        server_port = int(config_databoard.get_ramp_field('server_port'))
    else:
        server_port = int(port)
    app.run(
        debug=True,
        port=server_port,
        host='0.0.0.0')


# TODO: fill up the following functions so to easily deploy
# databoard on the server

# FIXME: dtach not working
#@hosts(production)
#def rserve(sockname="db_server"):
#    if not exists("/usr/bin/dtach"):
#        sudo("apt-get install dtach")
#
#    with cd(config_databoard.dest_path):
#        # run('export SERV_PORT={}'.format(server_port))
#        # run('fab serve')
#        # run('dtach -n `mktemp -u /tmp/{}.XXXX` export SERV_PORT={};fab serve'.format(sockname, server_port))
#        return run('dtach -n `mktemp -u /tmp/{}.XXXX` fab serve:port={}'.format(sockname, server_port))

#from importlib import import_module

software = [
    'fabfile.py',
    'ramp_index.txt',
    'databoard/config_databoard.py',
    'databoard/__init__.py',
    'databoard/fetch.py',
    'databoard/generic.py',
    'databoard/isotonic.py',
    'databoard/leaderboard.py',
    'databoard/machine_parallelism.py',
    'databoard/model.py',  # db model, TODO should be renamed
    'databoard/multiclass_prediction_type.py',
    'databoard/regression_prediction_type.py',
    'databoard/scores.py',
    'databoard/train_test.py',
    'databoard/views.py',
    'databoard/static',
    'databoard/templates',
]


def get_deployment_target(ramp_index, user, server, root):
    return config_databoard.get_ramp_field(user, ramp_index) + '@' \
        + config_databoard.get_ramp_field(server, ramp_index) + ":" \
        + config_databoard.get_destination_path(root, ramp_index=None)


def publish(ramp_index, local=False, test=False):
    ramp_name = config_databoard.get_ramp_field('ramp_name', ramp_index)
    # TODO: check if ramp_name is the same as in
    #      'ramps/' + ramp_name + '/specific.py'

    # we save ramp_index in the main dir so the deplyment can query itself
    # for example, in serve (to get the port number) and sepcific (to get
    # the number of CPUs). generic.get_ramp_index() reads it in
    with open('ramp_index.txt', 'w') as f:
        f.write(ramp_index)

    command = "rsync -pthrRvz -c "
    if not local:
        command += "--rsh=\'ssh -i " + os.path.expanduser("~")
        command += "/.ssh/datacamp/id_rsa -p 22\' "
    for file in software:
        command += file + " "
    if not config_databoard.is_same_web_and_train_servers(ramp_index) \
            and not local:
        command1 = command + get_deployment_target(
            ramp_index, 'web_user', 'web_server', 'web_root')
        print command1
        os.system(command1)
    if local:
        command2 = command + config_databoard.local_root
    else:
        command2 = command + get_deployment_target(
            ramp_index, 'train_user', 'train_server', 'train_root')
    print command2
    os.system(command2)

    # rsyncing specific
    command = "rsync -pthrvz -c "
    if not local:
        command += "--rsh=\'ssh -i " + os.path.expanduser("~")
        command += "/.ssh/datacamp/id_rsa -p 22\' "
    command += " ramps/" + ramp_name + "/specific.py "
    if not config_databoard.is_same_web_and_train_servers(ramp_index) \
            and not local:
        command1 = command + get_deployment_target(
            ramp_index, 'web_user', 'web_server', 'web_root')
        command1 += "/databoard/"
        print command1
        os.system(command1)
    if local:
        command2 = command + config_databoard.local_root
    else:
        command2 = command + get_deployment_target(
            ramp_index, 'train_user', 'train_server', 'train_root')
    command2 += "/databoard/"
    print command2
    os.system(command2)

    if test:
        command = "rsync -pthrvz -c "
        if not local:
            command += "--rsh=\'ssh -i " + os.path.expanduser("~")
            command += "/.ssh/datacamp/id_rsa -p 22\' "
        command += " ramps/" + ramp_name + "/submissions "
        if not config_databoard.is_same_web_and_train_servers(ramp_index) \
                and not local:
            command1 = command + get_deployment_target(
                ramp_index, 'web_user', 'web_server', 'web_root')
            print command1
            os.system(command1)
        if local:
            command2 = command + config_databoard.local_root
        else:
            command2 = command + get_deployment_target(
                ramp_index, 'train_user', 'train_server', 'train_root')
        print command2
        os.system(command2)


# (re)publish data set from 'ramps/' + ramp_name + '/data'
# fab setup_ground_truth should be run at the destination
def publish_data(ramp_index, local=False):
    ramp_name = config_databoard.get_ramp_field('ramp_name', ramp_index)
    command = "rsync --delete -pthrvz -c "
    if not local:
        command += "--rsh=\'ssh -i " + os.path.expanduser("~")
        command += "/.ssh/datacamp/id_rsa -p 22\' "
    command += 'ramps/' + ramp_name + '/data '
    if not config_databoard.is_same_web_and_train_servers(ramp_index) \
            and not local:
        command1 = command + get_deployment_target(
            ramp_index, 'web_user', 'web_server', 'web_root') + "/"
        print command1
        os.system(command1)
    if local:
        command2 = command + config_databoard.local_root
    else:
        command2 = command + get_deployment_target(
            ramp_index, 'train_user', 'train_server', 'train_root') + "/"
    print command2
    os.system(command2)
