## Summary

<!-- Brief description of changes -->

## Related Issues

<!-- Link to related issues: Closes #XX, Fixes #XX -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring (no functional change)
- [ ] Documentation
- [ ] CI/Infrastructure

## Checklist

### Required
- [ ] Tests added/updated (TDD-first: tests committed before implementation)
- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] No `as any`, `@ts-ignore`, or type suppressions

### Architecture Compliance
- [ ] **ADR-004**: No `add_messages` or `BaseMessage` usage in simulation code
- [ ] **ADR-004**: No LLM calls in data plane (Bronze/Silver/Gold/Entity Resolution)
- [ ] **ADR-005**: Report claims are JSON-first with evidence_ids (no direct prose generation)
- [ ] **ADR-003**: Simulation references explicit `dataset_snapshot_id`

### If applicable
- [ ] Documentation updated
- [ ] ADR created/updated for architectural decisions
- [ ] Benchmark scenario updated if behavior changed
