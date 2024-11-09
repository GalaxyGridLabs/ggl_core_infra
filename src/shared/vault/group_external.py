import pulumi_vault as pvault
import pulumi
from typing import List

class GroupExternal(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                group_name: str,
                policies: List[str],
                metadata: dict,
                auth_mount_accessor: str,
                opts = None):

        super().__init__('ggl:shared/vault:GroupExternal', name, None, opts)

        group = pvault.identity.Group(
            resource_name=name,
            name=group_name,
            type="external",
            policies=policies,
            metadata=metadata,
            opts=pulumi.ResourceOptions(parent=self))

        group_alias = pvault.identity.GroupAlias(
            resource_name=f"{name}-alias",
            name=group_name,
            mount_accessor=auth_mount_accessor,
            canonical_id=group.id,
            opts=pulumi.ResourceOptions(parent=self))
