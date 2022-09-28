# Operator Experiments

## Approach

Use the Operator SDK's [Helm plugin](https://sdk.operatorframework.io/docs/building-operators/helm/) to create CRDs for pelorus's core and each exporter type.

Modified the dependencies of the `pelorus` chart to not explicitly depend on exporters (keep it separate).

Add stuff to the API spec reflecting the configuration options for each exporter.

## Open Questions

- how granular should rbac be? It generated per exporter type, but I think it should just be for any exporters. Right?
- do we keep the helm charts as well as the ones copied into the operator?
  - keeping them means we can do releases while stuff is in the works.
  - but to deduplicate, we can/should symlink to them.
  - ...but then we can't keep the modifications we did above. Do we just need to be careful about that? Perhaps a simple pre-commit script add-on?

## TODO

- [ ] fill in config spec for CRDs other than deploytime (chosen for its simplicity)
- [ ] add samples for easy testing
- [ ] figure out the correct workflow for the makefile.
  - [ ] podman
  - [ ] get it working with the cluster internal registry