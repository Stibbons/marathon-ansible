ansible playbook and tools to run Forestscribe infra in marathon


    export ZK_HOST=<zk_host>:<zk_port>
    pipenv --two
    pipenv install --ignore-hashes
    pipenv run ansible-playbook marathon/core.yml
    pipenv run ansible-playbook marathon/ci.yml
    pipenv run ansible-playbook marathon/sota.yml


To populate zk with the ansible vault (only need to be done once, or when new infra configuration is to be done):

    cat 'XXX' > ~/.vault-password.forestscribe  # get this file from pierre
    export ZK_HOST=<zk_host>:<zk_port>
    ansible-playbook zk_populate.yml --vault-password-file=~/.vault-password.forestscribe

For Traefik related:

    export DOMAIN_EXT=<domainserver.ext>
    export ZK_HOST=<zk_host>:<zk_port>
    pipenv install --ignore-hashes
    pipenv run ansible-playbook marathon/traefik.yml
