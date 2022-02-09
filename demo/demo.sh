#!/usr/bin/env bash
set -e

if [[ ($# -lt 2) || $1 == "-h" || $1 == "--help" ]]; then
  echo "Usage: demo.sh PATH_TO_container-pipelines_REPO URL_OF_container-pipelines_REPO" >&2
  exit 1
fi

path=$1
url=$2

# Will create spring rest deployment
pushd "$path/basic-nginx"
   ansible-galaxy install -r requirements.yml --roles-path=galaxy
   ansible-playbook -i ./.applier/ galaxy/openshift-applier/playbooks/openshift-cluster-seed.yml -e skip_manual_promotion=true -e source_code_url="$url"
popd

# Run through a loop, so demo presenter can deploy as many sample apps, with commits, as necessary.
v1=$3
while :; do
  echo
  echo "The pipeline and first run of the demo app has started. When it has finished, you may rerun (with commits) or quit now."
  echo "1. Rerun with Commit"
  echo "2. Quit"
  echo -n "Type 1 or 2: "
  read -rn 1 a
  echo

  case $a in
  1* )
    echo "$v1"
    #Add Comment to a file to replicate a "change"
    echo "this is a comment" >> "$path/basic-nginx/index.html"

    # git commit
    pushd "$path"
      git add .
      git commit -m "doing a change"
      git push origin master
    popd

    #Redeploy app
    #in the *-build project
    oc start-build basic-nginx-pipeline -n "${nginx_namespace_prefix:-}basic-nginx-build"
  ;;

  2* )     exit 0;;
  
  * )     echo "Try again.";;
  esac
done

