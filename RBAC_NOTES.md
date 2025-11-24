# RBAC object pipeline

- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/resolvers/Insert.py` normalizes `rbacobject_id` for inserts (fallback to acting user id, recursive propagation through `InputModelMixin.set_rbacobject_id*`) and stamps metadata (`createdby_id`, uuids) before persistence.
- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/LoadDataExtension.py` hides the `db_row` argument from the public GraphQL schema and preloads the ORM row so that later extensions have the raw instance available.
- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/RbacProviderExtension.py` extracts `db_row.rbacobject_id` (falls back to `db_row.id`) and injects it back into the resolver call while emitting typed errors through `TwoStageGenericBaseExtension`.
- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/RbacInsertProviderExtension.py` mirrors the previous step for create operations by sourcing `rbacobject_id` straight from the Strawberry input object.

# Permission evaluation

- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/RolePermissionSchemaExtension.py` seeds the per-request `info.context` with three `GraphQLBatchLoader` instances pointing at the UG/RBAC GraphQL API so queries for `userCan*` and role listings are batched automatically.
- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/UserRoleProviderExtension.py` consumes `rbacobject_id`, fetches the acting user via `getUserFromInfo`, and loads roles through `userRolesForRBACQuery_loader`, hiding the `user_roles` argument from the schema.
- `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/UserAccessControlExtension.py` (object scoped) and `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/UserAbsoluteAccessControlExtension.py` (global) intersect allowed role-type names with the supplied roles, inject the `@permissionCheckRole` directive (via `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/ApplyPermissionCheckRoleDirectiveMixin.py`), and return a consistent “you are not authorized” error when no role matches.

# Replicating the pattern elsewhere

1. Expose hidden parameters on protected resolvers:
   - Updates: `extensions=[UserAccessControlExtension, UserRoleProviderExtension, RbacProviderExtension, LoadDataExtension]`.
   - Inserts: `extensions=[UserAccessControlExtension, UserRoleProviderExtension, RbacInsertProviderExtension]`.
   - Strawberry executes extensions in reverse order, so list them from last logical step to first.
2. Ensure the GraphQL executor places an authenticated `user` and UG client into `info.context`; otherwise role loaders cannot query the RBAC service.
3. Make insert/update inputs inherit from `InputModelMixin` and call `set_rbacobject_id` on the root to propagate the same RBAC object through nested dataclasses.
4. Keep schema documentation in sync by supplying `roles=[...]` when instantiating `UserAccessControlExtension`/`UserAbsoluteAccessControlExtension`; the mixin auto-adds the directive, so clients can introspect required permissions.
5. When extending the system, base new extensions on `/Users/josefkaspar/treti rocnik/uoishelpers/uoishelpers/gqlpermissions/TwoStageGenericBaseExtension.py` to reuse typed error creation and to make the new component composable with the existing pipeline.
