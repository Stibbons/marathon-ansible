ansible playbook and tools to run Forestscribe infra in marathon

    sudo -E pip install kazoo # (install on system needed for deploying Zookeeper tasks)
    export ZK_HOST=<zk_host>:<zk_port>
    pipenv --two
    pipenv install --ignore-hashes
    pipenv run ansible-playbook marathon/core.yml
    pipenv run ansible-playbook marathon/ci.yml
    pipenv run ansible-playbook marathon/sota.yml


To populate zk with the ansible vault (only need to be done once, or when new infra configuration is to be done):

    echo 'XXX' > ~/.vault-password.forestscribe  # get this file from pierre (ask him twice)
    export ZK_HOST=<zk_host>:<zk_port>
    pipenv run ansible-vault --vault-password-file=~/.vault-password.forestscribe -vvvv edit zk_init_file.yml
    pipenv run ansible-playbook zk_populate.yml --vault-password-file=~/.vault-password.forestscribe


For Traefik related:

    export ZK_HOST=<zk_host>:<zk_port>
    pipenv install --ignore-hashes
    pipenv run ansible-playbook marathon/traefik.yml
