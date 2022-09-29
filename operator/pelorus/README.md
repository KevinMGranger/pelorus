# Operator Experiments

## Approach

**NOTE**: I realized that one CRD per exporter type won't work (at least right now).
This is because the helm releases are named after the CR name. The kind isn't embedded in it.

Use the Operator SDK's [Helm plugin](https://sdk.operatorframework.io/docs/building-operators/helm/) to create CRDs for pelorus's core and each exporter type.

Modified the dependencies of the `pelorus` chart to not explicitly depend on exporters (keep it separate).

Add stuff to the API spec reflecting the configuration options for each exporter.

Added additional printer columns for the essential field(s): exporter type

## Chart modifications

- lifted exporters from dependency / sub-chart of pelorus into a standalone chart
- made exporters _singular_. Each exporter is now its own deployment
- made the app name(s) the release name, so it inherits the name from the CRD
- made certain config items top-level variables with camelCase naming (only deploytime for now, and only its specifics)

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