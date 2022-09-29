# Operator Experiments

## Approach

**NOTE**: another last-minute realization: it names helm releases per CR _Name_. It's not namespaced or anything. What??? Nonsensical.

**NOTE**: I realized that one CRD per exporter type won't work (at least right now).
This is because the helm releases are named after the CR name. The kind isn't embedded in it.

Use the Operator SDK's [Helm plugin](https://sdk.operatorframework.io/docs/building-operators/helm/) to create CRDs for pelorus's core and each exporter type.

Modified the dependencies of the `pelorus` chart to not explicitly depend on exporters (keep it separate).

Add stuff to the API spec reflecting the configuration options for each exporter.

Added additional printer columns for the essential field(s): exporter type

### Helm Limitation:

Helm Operators from the Operator SDK-- the releases they create are named after the Custom Resource's name, with no namespacing. That means that a `foo.example.com/v1/Frobnicator/NameHere` conflicts with a `bar.example.com/v2/Widget/NameHere`.

Looks like this is acknowledged in the docs for `release.getReleaseName`: https://github.com/operator-framework/operator-sdk/blob/b97d84fc19c67f5c9a2e4c10ada1a8000424e63e/internal/helm/release/manager_factory.go#L117

The PR in question: https://github.com/operator-framework/operator-sdk/pull/1818

> Description of the change:
> This changes the release name for new CRs to be the CR name. Releases for existing CRs will continue to use the legacy name. If a CR is created, and a release already exists with the same name from a CR of a different kind, an error is returned, indicating a duplicate name.
> 
> Motivation for the change:
> The reason for this change is based on an interaction between the Kubernetes constraint that limits label values to 63 characters and the Helm convention of including the release name as a label on release resources.
> 
> Since the legacy release name includes a 25-character value based on the parent CR's UID, it leaves little extra space for the CR name and any other identifying names or characters added by templates.

Now, helm embedding a label with the release name is merely a _convention_.

But... that was merged a few months before Helm v3 came out. In helm v3, 

### Chart modifications

- lifted exporters from dependency / sub-chart of pelorus into a standalone chart
- made exporters _singular_. Each exporter is now its own deployment
- made the app name(s) the release name, so it inherits the name from the CRD
- made certain config items top-level variables with camelCase naming (only deploytime for now, and only its specifics)

### User Adoption

- A script to adapt configmaps and values.yml files would be easy to make
- We can keep support for configmaps, and will of course need to keep that for secrets

## Analysis

### Advantages
- only moderate modifications to current approach

### Unknowns
- what does an upgrade path look like? (e.g. eventually separating CRDs per exporter type)

## Open Questions

- should we get even more specific with our charts for now, just for better config support?
- how granular should rbac be? It generated per exporter type, but I think it should just be for any exporters. Right?
- do we keep the helm charts as well as the ones copied into the operator?
  - keeping them means we can do releases while stuff is in the works.
  - but to deduplicate, we can/should symlink to them.
  - ...but then we can't keep the modifications we did above. Do we just need to be careful about that? Perhaps a simple pre-commit script add-on?

- TODO: is it possible to restrict the fields for the exporters based on their type?
  - CRDs can't use `discriminator`, but can you use a literal with `pattern`?

## TODO

- [ ] fill in config spec for CRDs other than deploytime (chosen for its simplicity)
- [ ] add printer columns for backend types for other exporters
- [ ] add spots for extra extensions (e.g. env vars)
- [ ] add samples for easy testing
- [ ] figure out the correct workflow for the makefile.
  - [ ] podman
  - [ ] get it working with the cluster internal registry
- [ ] verify how default and nullable interact

## Future Ideas

Ultra-simple web interface that checks that you have things deployed correctly (e.g. did you deploy a pelorus core and some number of exporters? Are there running grafana and prometheus instances?)