# Commit Time Exporter

The job of the commit time exporter is to find and associate time of the relevant source code commit with a container image SHA built from that source code.

This information can be found in two ways:

- [Git API](#using-commit-time-with-git-apis) making a request to the Git provider

- [Containers' Image](#using-commit-time-with-images) querying `Annotations` or `Labels` within the Image object, without reaching to the git external services. For the image Time provider, the Commit Date must be present as a valid string. This allows to give greater flexibility around 3rd party CI systems used to create container images for the OpenShift running applications.


Later the Deploy Time Exporter can associate that image SHA with a production deployment and allow to calculate [Lead Time for Change](../../philosophy/outcomes/SoftwareDeliveryPerformance.md#lead-time-for-change) metrics.

> **NOTE:** It is important to deploy a `committime` exporter instance per unique Source Control provider. So if your monitored applications uses container images that are built from the source code hosted in the GitHub, Gitea, and two different self hosted BitBucket systems, you would need to create four committime instances.


## Using Commit Time with Git APIs

This is the default method of gathering commit time from the source code that triggered container build. Git commit hash and FQDN from the Build metadata are used to perform a query to a [supported Git API](../Overview.md#supported-providers) and collect commit time.

We require that all builds associated with a particular application be labeled with the same `app.kubernetes.io/name=<app_name>` label. Different label name may be used with provided exporter instance configuration option [APP_LABEL](#app_label).

In some cases, such as binary build the `Build` object may be missing information required to gather Git commit time. Refer to the [Annotations and local build support](#annotations-and-local-build-support) for information how to enable Commit Time Exporter for such builds.

## Using Commit Time with Images

This is the method of gathering source commit time associated directly with an `Image` object, where `Build` object may be missing.

It may be used in a situations where 3rd party build systems are building container images for our application deployment.

Using Commit Time exporter with images requires setting [PROVIDER](#provider) to `image`, see [example](#example) and synonymously annotating the Image object. Please refer to the [Annotations, Docker Labels and Image support](#annotations-docker-labels-and-image-support) for an detailed workflow example of how to use Commit Time Exporter with Images.

## Example

Pelorus configuration object YAML file with three `committime` exporters:

  - First exporter `committime-github` monitors two namespaces `my-application1` and `my-application2`. The source code that was used to build the container images for the running application is hosted in the public [GitHub](https://github.com/) service.
  - Second exporter `committime-exporter2` monitors `my-application3` namespace in which running application is using container image that was built from the bitbucket source code. This source code is on the self-hosted BitBucket service. API to that BitBucket is accessible from `api.bitbucket.mydomain.com`.
  - Third exporter is using [image](#using-commit-time-with-images) to gather commit date which was used for the deployment directly from the Image annotation `myapp.build.commit.date` that uses date format `%a %b %d %H:%M:%S %Y %z`. This annotation has to be provided by 3rd party systems such as different flavour CI systems. This exporter does not query any external API endpoint.

```yaml
apiVersion: charts.pelorus.konveyor.io/v1alpha1
kind: Pelorus
metadata:
  name: sample-pelorus-deployment
spec:
  exporters:
    instances:
      - app_name:  committime-github
        exporter_type: committime
        extraEnv:
          - name: GIT_PROVIDER
            value: github
          - name: NAMESPACES
            value: my-application1,my-application2
          - name: TOKEN
            value: <github_token>

      - app_name: committime-exporter2
        exporter_type: committime
        extraEnv:
          - name: GIT_PROVIDER
            value: bitbucket
          - name: GIT_API
            value: api.bitbucket.mydomain.com
          - name: API_USER
            value: <bitbucket_user>
          - name: TOKEN
            value: <bitbucket_token>
          - name: NAMESPACES
            value: my-application3

      - app_name: committime-exporter3
        exporter_type: committime
        extraEnv:
          - name: PROVIDER
            value: image
          - name: COMMIT_DATE_ANNOTATION
            value: myapp.build.commit.date
          - name: COMMIT_DATE_FORMAT
            value: '%a %b %d %H:%M:%S %Y %z'
```

## Commit Time Exporter configuration options

This is the list of options that can be applied to `env_from_secrets`, `env_from_configmaps` and `extraEnv` section of a Commit time exporter.

Table below represents configuration options, which are valid for any Commit Time Exporter instance.
There are additional options available when the [PROVIDER](#provider) type is set to `git` or `image`:

- [➔ PROVIDER `git` options](#provider-git-options) (same as unset [PROVIDER](#provider) option)
- [➔ PROVIDER `image` options](#provider-image-options)

| Variable | Required | Default Value |
|----------|----------|---------------|
| [LOG_LEVEL](#log_level) | no | `INFO` |
| [APP_LABEL](#app_label) | no | `app.kubernetes.io/name` |
| [PELORUS_DEFAULT_KEYWORD](#pelorus_default_keyword) | no | `default` |
| [COMMIT_HASH_ANNOTATION](#commit_hash_annotation) | no | `io.openshift.build.commit.id` |
| [COMMIT_REPO_URL_ANNOTATION](#commit_repo_url_annotation) | no | `io.openshift.build.source-location` |
| [PROVIDER](#provider) | no | `git` |

###### LOG_LEVEL

- **Required:** no
    - **Default Value:** INFO
- **Type:** string

: Set the log level. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`.

###### APP_LABEL

- **Required:** no
    - **Default Value:** app.kubernetes.io/name
- **Type:** string

: Changes the label key used to identify applications.

###### PELORUS_DEFAULT_KEYWORD

- **Required:** no
    - **Default Value:** default
- **Type:** string

: Used only when configuring instance using ConfigMap. It is the ConfigMap value that represents `default` value. If specified it's used in other data values to indicate "Default Value" should be used.

###### COMMIT_HASH_ANNOTATION

- **Required:** no
    - **Default Value:** io.openshift.build.commit.id
- **Type:** string

: Annotation name associated with the Build from which hash is used to calculate commit time.

###### COMMIT_REPO_URL_ANNOTATION

- **Required:** no
    - **Default Value:** io.openshift.build.source-location
- **Type:** string

: Annotation name associated with the Build from which GIT repository URL is used to calculate commit time.

###### PROVIDER

- **Required:** no
    - **Default Value:** git
- **Type:** string

: Provider from which commit date is taken. One of `git`, `image`.
> **NOTE:** For detailed instructions please refer to the:
>
- [Using Commit Time with Git APIs](#using-commit-time-with-git-apis) for the `git` PROVIDER
- [Using Commit Time with Images](#using-commit-time-with-images) for the `image` PROVIDER

#### ➔ [PROVIDER](#provider) `git` options

Those options are only applicable to the Commit Time Exporter when the [PROVIDER](#provider) is set to `git` or the [PROVIDER](#provider) option is unset.

| Variable | Required | Default Value |
|----------|----------|---------------|
| [NAMESPACES](#namespaces) | no | - |
| [GIT_PROVIDER](#git_provider) | no | github |
| [API_USER](#api_user) | yes | - |
| [TOKEN](#token) | yes | - |
| [GIT_API](#git_api) | yes | [see more...](#git_api) |

###### NAMESPACES

- **Required:** no
    - Only applicable for [PROVIDER](#provider) value: `git` or unset
    - **Default Value:** unset; scans all namespaces
- **Type:** comma separated list of strings

: Restricts the set of namespaces from which metrics will be collected.

###### GIT_PROVIDER

- **Required:** no
    - Only applicable for [PROVIDER](#provider) value: `git` or unset
    - **Default Value:** github
- **Type:** string

: Set Git provider type. Can be `github`, `bitbucket`, `gitea`, `azure-devops` or `gitlab`

###### API_USER

- **Required:** yes
    - Only applicable for [PROVIDER](#provider) value: `git` or unset
- **Type:** string

: GIT API username.

###### TOKEN

- **Required:** yes
    - Only applicable for [PROVIDER](#provider) value: `git` or unset
- **Type:** string

: User's Git API Token

###### GIT_API

- **Required:** yes
    - Only applicable for [PROVIDER](#provider) value: `git` or unset
    - **Default Value:**
        - `api.github.com` for `github` [GIT_PROVIDER](#git_provider)
        - `dev.azure.com` for `azure-devops` [GIT_PROVIDER](#git_provider)
        - `try.gitea.io` for `gitea` [GIT_PROVIDER](#git_provider)
        - **unset** for `gitlab` [GIT_PROVIDER](#git_provider)
        - **unset** for `bitbucket` [GIT_PROVIDER](#git_provider)
- **Type:** string

: GitHub, Gitea or Azure DevOps API FQDN. This allows the override for Enterprise users.

#### ➔ [PROVIDER](#provider) `image` options

Those options are only applicable to the Commit Time Exporter when the [PROVIDER](#provider) is set to `image`.

| Variable | Required | Default Value |
|----------|----------|---------------|
| [COMMIT_DATE_ANNOTATION](#api_user) | no | `io.openshift.build.commit.date` |
| [COMMIT_DATE_FORMAT](#token) | no | `%a %b %d %H:%M:%S %Y %z` |

###### COMMIT_DATE_ANNOTATION

- **Required:** no
    - Only applicable for [PROVIDER](#provider) value: `image`
    - **Default Value:** io.openshift.build.commit.date
- **Type:** string

: Annotation name associated with the Image from which commit time is taken.
: 
> **NOTE:** The date and time found in the OpenShift object [COMMIT_DATE_ANNOTATION](#commit_date_annotation) annotation will be calculated by parsing it's value string in the following order:
> 
- 10 digit EPOCH timestamp. Allowed EPOCH string format is one, where milliseconds are ignored.
- The one from the [COMMIT_DATE_FORMAT](#commit_date_format)
>
> Please refer to the [Annotations, Docker Labels and Image support](#annotations-docker-labels-and-image-support) for an example.

###### COMMIT_DATE_FORMAT

- **Required:** no
    - Only applicable for [PROVIDER](#provider) value: `image`
    - **Default Value:** %a %b %d %H:%M:%S %Y %z
- **Type:** string

: Used when the format is different then 10 digit EPOCH timestamp.
: Format in `1989 C standard` to convert time and date found in the Image Label `io.openshift.build.commit.date` or annotation for the Image.

## Annotations and local build support

Commit Time Exporter may be used in conjunction with Builds **where values required to gather commit time from the source repository are missing**. In such case each Build is required to be annotated with two values allowing Commit Time Exporter to calculate metric from the Build.

To annotate Build use the following commands:

```shell
oc annotate build <build-name> -n <namespace> --overwrite io.openshift.build.commit.id=<commit_hash>

oc annotate build <build-name> -n <namespace> --overwrite io.openshift.build.source-location=<repo_uri>
```

Custom Annotation names may also be configured using Commit Time Exporter [COMMIT_HASH_ANNOTATION](#commit_hash_annotation) and [COMMIT_REPO_URL_ANNOTATION](#commit_repo_url_annotation) options.

> **Note:** The requirement to label the build with `app.kubernetes.io/name=<app_name>` for the annotated Builds applies.

### Example workflow for an OpenShift binary build

* Sample Application

```shell
cat app.py
#!/usr/bin/env python3
print("Hello World")
```

* Binary build steps

```shell
NS=binary-build
NAME=python-binary-build

oc create namespace "${NS}"

oc new-build python --name="${NAME}" --binary=true -n "${NS}"  -l "app.kubernetes.io/name=${NAME}"
oc start-build "bc/${NAME}" --from-file=./app.py --follow -n "${NS}"

oc get builds -n "${NS}"
oc -n "${NS}" annotate build "${NAME}-1" --overwrite \
io.openshift.build.commit.id=7810f2a85d5c89cb4b17e9a3208a311af65338d8 \
io.openshift.build.source-location=http://github.com/konveyor/pelorus

oc -n "${NS}" new-app "${NAME}" -l "app.kubernetes.io/name=${NAME}"
```

### Additional Examples

There are many ways to build and deploy applications in OpenShift. Additional examples of how to annotate builds such that Pelorus will properly discover the commit metadata can be found in the  [Pelorus tekton demo](https://github.com/konveyor/pelorus/tree/master/demo)

## Annotations, Docker Labels and Image support

Image object annotations similarly to [Annotations and local build support](#annotations-and-local-build-support) may be used for the Commit Time Exporter **where values from the Build objects required to gather commit time from the source repository are missing**.

> **Note:** The requirement to label the image SHA with `app.kubernetes.io/name=<app_name>` for the annotated or Labeled Image objects applies.

Custom Annotation names may also be configured using Commit Time Exporter [COMMIT_DATE_ANNOTATION](#commit_date_annotation) option.

An Image object which is a result of Docker or Source-to-Image (S2I) builds set includes Docker Label `io.openshift.build.commit.date` metadata from which Commit Time Exporter gets the commit date. In such case Image object do not need to be annotated.

Example image metadata with `io.openshift.build.commit.date` Docker Labels and `app.kubernetes.io/name=<app_name>` Label required for the Commit Time Exporter:

```shell
IMAGE_SHA=588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e

$ oc describe image "sha256:${IMAGE_SHA}"

Docker Image:	image-registry.openshift-image-registry.svc:5000/mongo-persistent/todolist-mongo-go@sha256:588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e
Name:		    sha256:588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e
[...]
Labels:		    app.kubernetes.io/name=my-demo-application
[...]
Docker Labels:	io.buildah.version=1.22.4
		        io.openshift.build.commit.author=Wesley Hayutin <weshayutin@gmail.com>
		        io.openshift.build.commit.date=Mon Aug 8 13:13:58 2022 -0600
		        io.openshift.build.commit.id=b6abfb214557289bdaa9bed3dcc570ffd5b9ad4f
		        io.openshift.build.commit.message=Merge pull request #90 from mpryc/master
		        io.openshift.build.commit.ref=master
		        io.openshift.build.name=todolist-1
		        io.openshift.build.namespace=mongo-persistent
		        io.openshift.build.source-location=https://github.com/konveyor/mig-demo-apps.git
```

To annotate Image and ensure Commit Time Exporter can gather relevant values, use `oc annotate` CLI as in the following example:

```shell
$ NAME=my-application
$ IMAGE_SHA=588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e
$ oc label image "sha256:${IMAGE_SHA}" "app.kubernetes.io/name=${NAME}"

# In case image already has the `app.kubernetes.io/name` label, use --overwrite CLI option
$ oc label image "sha256:${IMAGE_SHA}" --overwrite "app.kubernetes.io/name=${NAME}"

> image.image.openshift.io/sha256:588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e labeled

$ oc annotate image "sha256:${IMAGE_SHA}" --overwrite \
     io.openshift.build.commit.date="Mon Aug 8 13:13:58 2022 -0600"

> image.image.openshift.io/sha256:588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e annotated

# It's not necessary for the Pelorus metric, but for completeness of the data, you may also annotate Git commit corresponding
# with the Image build:

$ oc annotate image "sha256:${IMAGE_SHA}" --overwrite \
    io.openshift.build.commit.id=b6abfb214557289bdaa9bed3dcc570ffd5b9ad4f \
    io.openshift.build.commit.date="Mon Aug 8 13:13:58 2022 -0600"

> image.image.openshift.io/sha256:588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e annotated
```

The Image may be also annotated with 10 digit EPOCH timestamp. Allowed format is one, where milliseconds are ignored:

```shell
$ EPOCH_TIMESTAMP=`git log -1 --format=%ct`
$ echo ${EPOCH_TIMESTAMP}
1663770655

$ NAME=my-application
$ IMAGE_SHA=588fb67a63ccbadf245b6d30747c404d809a851551b67c615a18217bf443a78e
$ oc label image "sha256:${IMAGE_SHA}" "app.kubernetes.io/name=${NAME}"

$ oc annotate image "sha256:${IMAGE_SHA}" --overwrite \
     io.openshift.build.commit.date="${EPOCH_TIMESTAMP}"
```