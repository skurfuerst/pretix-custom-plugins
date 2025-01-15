{ pkgs, pretix, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [ pkgs.git pkgs.rsync ];
  languages.python = {
    enable = true;
    venv.enable = true;
  };
  starship.enable = true;

  # https://devenv.sh/scripts/
  scripts.init-pretix.exec = ''
    THISDIR=$(pwd)
    rsync -a ${pretix}/ $THISDIR/.devenv/pretix
    pushd $THISDIR/.devenv/pretix
    chmod -R 777 $THISDIR/.devenv/pretix
    # TODO: PIP_CACHE_DIR set
    pip3 install wheel
    pip3 install -e ".[dev]"

    pushd src
    python manage.py collectstatic --noinput
    cp $THISDIR/.docker-dev/pretix.cfg .
    python manage.py migrate
    popd

    popd
  '';
  
  services.postgres = {
    enable = true;
    listen_addresses = "127.0.0.1";
    initialDatabases = [
      { name = "pretix"; }
    ];
    initialScript = ''
      CREATE USER pretix SUPERUSER;
    '';
  };
  services.redis.enable = true;


  # https://devenv.sh/languages/
  # languages.nix.enable = true;

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # https://devenv.sh/processes/
  # processes.ping.exec = "ping example.com";

  # See full reference at https://devenv.sh/reference/options/
}
