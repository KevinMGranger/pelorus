#!/usr/bin/env bash
#Assumes User is logged in to cluster
set -euo pipefail

Help()
{
   # Display Help
   echo "Execute a tekton pipeline with various build types."
   echo
   echo "Syntax: scriptTemplate [-h|g|b|]"
   echo "options:"
   echo "g     the git url"
   echo "r     git branch reference, use this for Pull Requests. e.g. refs/pull/587/head"
   echo "h     Print this Help."
   echo "b     build type [buildconfig, binary, s2i]"
   echo
}

# Defaults
current_branch="$(git symbolic-ref HEAD)"
current_branch=${current_branch##refs/heads/}
url="https://github.com/konveyor/pelorus"
build_type="binary"

# Get the options
while getopts ":hg:b:r:" option; do
   case $option in
      h) # display Help
         Help
         exit;;
      g) # Enter the git url
         url=$OPTARG;;
      r) # the git ref
         current_branch=$OPTARG;;
      b) # Enter the build type 
         build_type=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

echo "============================"
echo "Executing the basic-python-tekton demo for Pelorus..."
echo ""
echo "*** Current Options used ***"
echo "Git URL: $url"
echo "Git ref: $current_branch"
echo "Build Type: $build_type"
echo "============================"
echo ""


all_cmds_found=0
for cmd in oc tkn; do
   if ! command -v $cmd &> /dev/null; then
      echo "No $cmd executable found in $PATH" >&2
      all_cmds_found=1
   fi
done
if ! [[ $all_cmds_found ]]; then exit 1; fi


tekton_setup_dir="$(dirname "${BASH_SOURCE[0]}")/tekton-demo-setup"
python_example_txt="$(dirname "${BASH_SOURCE[0]}")/python-example/response.txt"

echo "Create and/or switch to the basic-python-tekton namespace"
if ! new_project_output="$(oc new-project basic-python-tekton 2>&1)"; then
   if echo "$new_project_output" | grep -q "AlreadyExists"; then
      echo "Project already exists"
   else
      echo "$new_project_output" >&2
      exit 1
   fi
else
   echo "$new_project_output"
fi

oc project basic-python-tekton
      
echo "Clean up resources prior to execution:"
# cleaning resources vs. deleting the namespace to preserve pipeline run history
# resources are cleaned to ensure that the new running artifact is from the latest build
oc delete --all imagestream -n basic-python-tekton &> /dev/null || true
oc scale dc/basic-python-tekton --replicas=0 &> /dev/null || true
oc delete dc/basic-python-tekton -n basic-python-tekton &> /dev/null || true
oc delete buildConfig basic-python-tekton &> /dev/null || true
oc delete buildconfig.build.openshift.io/basic-python-tekton &> /dev/null || true
oc delete -all pods -n basic-python-tekton  &> /dev/null || true
oc delete --all replicationcontroller -n basic-python-tekton &> /dev/null || true

echo "Setting up resources:"

echo "1. Installing tekton operator"
oc apply -f "$tekton_setup_dir/01-tekton-operator.yaml"

echo "2. Setting up Build and Deployment Resources"
oc process -f "$tekton_setup_dir/02-build-and-deploy.yaml" > /tmp/02-build-and-deploy.yaml.out 2>/tmp/02-build-and-deploy.yaml.err
oc apply -f /tmp/02-build-and-deploy.yaml.out

echo "3. Setting up tekton pipeline"
oc process -f "$tekton_setup_dir/03-pipeline.yaml" > /tmp/03-pipeline.yaml.out 2>/tmp/03-pipeline.yaml.err
oc apply -f /tmp/03-pipeline.yaml.out

route="$(oc get -n basic-python-tekton route/basic-python-tekton --output=go-template='http://{{.spec.host}}')"

counter=1

function run_pipeline {
   tkn pipeline start -n basic-python-tekton --showlog basic-python-tekton-pipeline \
      -w name=repo,claimName=basic-python-tekton-build-pvc \
      -p git-url="$url" -p git-revision="$current_branch" \
      -p BUILD_TYPE="$build_type"
}

echo -e "\nRunning pipeline\n"
run_pipeline

echo -e "\nWhen ready, page will be available at $route"

while true; do
   echo ""
   echo "The pipeline and first run of the demo app has started. When it has finished, you may rerun (with commits) or quit now."
   echo "1. Rerun with Commit"
   echo "2. Quit"
   echo "3. Rerun without committing"
   read -r -p "Type 1 or 2: " -n 1 a
   echo ""
   case $a in
      1* )
         echo "We've modified this file, time to build and deploy a new version. Times modified: $counter" | tee -a "$python_example_txt"
         git commit -m "modifying python example, number $counter" -- "$python_example_txt"
         git push origin "$current_branch"

         run_pipeline

         echo -e "\nWhen ready, page will be available at $route"

         counter=$((counter+1))
      ;;

      2* ) exit 0 ;;
      3* )
         echo "Rerunning pipeline"
         run_pipeline
      ;;
         
      * ) echo "I'm not sure what $a means, please give 1 or 2" >&2 ;;
   esac
done

