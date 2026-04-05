"""Git-like scenario branching for simulations."""

import logging
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.database import BranchRepository

logger = logging.getLogger(__name__)


class ScenarioBranch(BaseModel):
    """A single branch in a scenario tree."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    name: str
    description: str
    config_diff: dict  # What changed from parent
    simulation_id: str | None = None  # Associated simulation
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator: str = ""


class ScenarioTree(BaseModel):
    """Complete scenario tree with all branches."""

    root_id: str
    branches: dict[str, ScenarioBranch]


class ScenarioBranchManager:
    """Manages Git-like scenario branching."""

    def __init__(self):
        self._trees: dict[str, ScenarioTree] = {}
        self._branch_index: dict[str, str] = {}  # branch_id -> root_id mapping
        self._repo = BranchRepository()

    async def create_branch(
        self,
        parent_branch_id: str,
        name: str,
        config_changes: dict,
        description: str = "",
        creator: str = "",
    ) -> ScenarioBranch:
        """Create a new branch from parent with config changes.

        Args:
            parent_branch_id: ID of the parent branch
            name: Name for the new branch
            config_changes: Dictionary of configuration changes
            description: Optional description
            creator: Optional creator identifier

        Returns:
            The newly created ScenarioBranch

        Raises:
            ValueError: If parent branch not found
        """
        # Find the tree containing the parent branch
        root_id = self._branch_index.get(parent_branch_id)

        if not root_id:
            # Check if this is a root branch request
            if parent_branch_id in self._trees:
                root_id = parent_branch_id
            else:
                raise ValueError(f"Parent branch not found: {parent_branch_id}")

        tree = self._trees[root_id]

        # Verify parent exists in tree
        if parent_branch_id not in tree.branches:
            raise ValueError(f"Parent branch not found in tree: {parent_branch_id}")

        # Create new branch
        new_branch = ScenarioBranch(
            parent_id=parent_branch_id,
            name=name,
            description=description or f"Branch from {parent_branch_id}",
            config_diff=config_changes,
            creator=creator,
        )

        # Add to tree
        tree.branches[new_branch.id] = new_branch
        self._branch_index[new_branch.id] = root_id

        # Persist to DB
        try:
            await self._repo.save_branch(
                {
                    "id": new_branch.id,
                    "root_id": root_id,
                    "parent_id": parent_branch_id,
                    "name": new_branch.name,
                    "description": new_branch.description,
                    "config_diff": new_branch.config_diff,
                    "simulation_id": new_branch.simulation_id,
                    "created_at": new_branch.created_at,
                    "creator": new_branch.creator,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save branch to DB: {e}")

        logger.info(f"Created branch {new_branch.id} from {parent_branch_id}")

        return new_branch

    async def create_root_branch(
        self,
        name: str,
        base_config: dict,
        description: str = "",
        creator: str = "",
    ) -> ScenarioBranch:
        """Create a new root branch (new scenario tree).

        Args:
            name: Name for the root branch
            base_config: Base configuration
            description: Optional description
            creator: Optional creator identifier

        Returns:
            The newly created root ScenarioBranch
        """
        # Create root branch
        root_branch = ScenarioBranch(
            parent_id=None,
            name=name,
            description=description or f"Root scenario: {name}",
            config_diff=base_config,
            creator=creator,
        )

        # Create new tree
        tree = ScenarioTree(
            root_id=root_branch.id,
            branches={root_branch.id: root_branch},
        )

        # Store tree
        self._trees[root_branch.id] = tree
        self._branch_index[root_branch.id] = root_branch.id

        # Persist to DB
        try:
            await self._repo.save_branch(
                {
                    "id": root_branch.id,
                    "root_id": root_branch.id,
                    "parent_id": None,
                    "name": root_branch.name,
                    "description": root_branch.description,
                    "config_diff": root_branch.config_diff,
                    "simulation_id": root_branch.simulation_id,
                    "created_at": root_branch.created_at,
                    "creator": root_branch.creator,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save root branch to DB: {e}")

        logger.info(f"Created root branch {root_branch.id} for scenario: {name}")

        return root_branch

    async def get_tree(self, root_id: str) -> ScenarioTree:
        """Get the full scenario tree.

        Args:
            root_id: ID of the root branch

        Returns:
            ScenarioTree with all branches

        Raises:
            ValueError: If tree not found
        """
        # Try in-memory first
        if root_id in self._trees:
            return self._trees[root_id]

        # Load from DB
        try:
            branches = await self._repo.get_branches_by_root(root_id)
            if branches:
                branch_dict = {}
                for b in branches:
                    branch = ScenarioBranch(
                        id=b["id"],
                        parent_id=b.get("parent_id"),
                        name=b["name"],
                        description=b.get("description", ""),
                        config_diff=b.get("config_diff", {}),
                        simulation_id=b.get("simulation_id"),
                        created_at=b["created_at"],
                        creator=b.get("creator", ""),
                    )
                    branch_dict[b["id"]] = branch
                    self._branch_index[b["id"]] = root_id

                tree = ScenarioTree(root_id=root_id, branches=branch_dict)
                self._trees[root_id] = tree
                return tree
        except Exception as e:
            logger.warning(f"Failed to load tree from DB: {e}")

        raise ValueError(f"Scenario tree not found: {root_id}")

    async def get_branch(self, branch_id: str) -> ScenarioBranch | None:
        """Get a specific branch by ID.

        Args:
            branch_id: The branch ID

        Returns:
            ScenarioBranch or None if not found
        """
        # Try in-memory first
        root_id = self._branch_index.get(branch_id)
        if root_id:
            tree = self._trees.get(root_id)
            if tree and branch_id in tree.branches:
                return tree.branches.get(branch_id)

        # Load from DB
        try:
            b = await self._repo.get_branch(branch_id)
            if b:
                return ScenarioBranch(
                    id=b["id"],
                    parent_id=b.get("parent_id"),
                    name=b["name"],
                    description=b.get("description", ""),
                    config_diff=b.get("config_diff", {}),
                    simulation_id=b.get("simulation_id"),
                    created_at=b["created_at"],
                    creator=b.get("creator", ""),
                )
        except Exception as e:
            logger.warning(f"Failed to load branch from DB: {e}")

        return None

    async def compare_branches(self, branch_ids: list[str]) -> dict:
        """Side-by-side comparison of up to 5 branches.

        Args:
            branch_ids: List of branch IDs to compare (max 5)

        Returns:
            Dictionary with comparison results

        Raises:
            ValueError: If more than 5 branches or branch not found
        """
        if len(branch_ids) > 5:
            raise ValueError("Cannot compare more than 5 branches at once")

        branches = []
        for branch_id in branch_ids:
            branch = await self.get_branch(branch_id)
            if not branch:
                raise ValueError(f"Branch not found: {branch_id}")
            branches.append(branch)

        # Build comparison
        comparison = {
            "branches_compared": len(branches),
            "branch_details": [],
            "common_config": {},
            "divergent_configs": {},
        }

        for branch in branches:
            comparison["branch_details"].append(
                {
                    "id": branch.id,
                    "name": branch.name,
                    "description": branch.description,
                    "parent_id": branch.parent_id,
                    "creator": branch.creator,
                    "created_at": branch.created_at,
                }
            )

        # Find common and divergent configuration keys
        all_keys = set()
        for branch in branches:
            all_keys.update(branch.config_diff.keys())

        for key in all_keys:
            values = [branch.config_diff.get(key) for branch in branches]
            if len(set(str(v) for v in values)) == 1:
                comparison["common_config"][key] = values[0]
            else:
                comparison["divergent_configs"][key] = {branch.id: branch.config_diff.get(key) for branch in branches}

        return comparison

    async def diff_configs(self, branch_a_id: str, branch_b_id: str) -> dict:
        """Show config differences between two branches.

        Args:
            branch_a_id: First branch ID
            branch_b_id: Second branch ID

        Returns:
            Dictionary with detailed diff

        Raises:
            ValueError: If either branch not found
        """
        branch_a = await self.get_branch(branch_a_id)
        branch_b = await self.get_branch(branch_b_id)

        if not branch_a:
            raise ValueError(f"Branch not found: {branch_a_id}")
        if not branch_b:
            raise ValueError(f"Branch not found: {branch_b_id}")

        diff = {
            "branch_a": {"id": branch_a.id, "name": branch_a.name},
            "branch_b": {"id": branch_b.id, "name": branch_b.name},
            "added_in_b": {},
            "removed_in_b": {},
            "modified": {},
            "unchanged": {},
        }

        config_a = branch_a.config_diff
        config_b = branch_b.config_diff

        all_keys = set(config_a.keys()) | set(config_b.keys())

        for key in all_keys:
            val_a = config_a.get(key)
            val_b = config_b.get(key)

            if key not in config_a:
                diff["added_in_b"][key] = val_b
            elif key not in config_b:
                diff["removed_in_b"][key] = val_a
            elif val_a != val_b:
                diff["modified"][key] = {"from": val_a, "to": val_b}
            else:
                diff["unchanged"][key] = val_a

        return diff

    async def get_branch_lineage(self, branch_id: str) -> list[ScenarioBranch]:
        """Get the lineage (path from root) for a branch.

        Args:
            branch_id: The branch ID

        Returns:
            List of branches from root to the specified branch

        Raises:
            ValueError: If branch not found
        """
        branch = await self.get_branch(branch_id)
        if not branch:
            raise ValueError(f"Branch not found: {branch_id}")

        lineage = [branch]
        current_id = branch.parent_id

        # Walk up the tree
        visited = {branch_id}  # Prevent infinite loops
        while current_id:
            if current_id in visited:
                raise ValueError("Circular reference detected in branch lineage")
            visited.add(current_id)

            parent = await self.get_branch(current_id)
            if not parent:
                break

            lineage.insert(0, parent)
            current_id = parent.parent_id

        return lineage

    async def merge_branch_config(self, source_branch_id: str, target_branch_id: str) -> dict:
        """Merge configuration from source branch into target.

        Args:
            source_branch_id: Source branch ID
            target_branch_id: Target branch ID

        Returns:
            Merged configuration dictionary

        Raises:
            ValueError: If either branch not found
        """
        source = await self.get_branch(source_branch_id)
        target = await self.get_branch(target_branch_id)

        if not source:
            raise ValueError(f"Source branch not found: {source_branch_id}")
        if not target:
            raise ValueError(f"Target branch not found: {target_branch_id}")

        # Start with target config and overlay source changes
        merged = dict(target.config_diff)
        merged.update(source.config_diff)

        return merged

    async def list_all_trees(self) -> list[dict]:
        """List all scenario trees.

        Returns:
            List of tree summaries
        """
        summaries = []
        for root_id, tree in self._trees.items():
            root_branch = tree.branches.get(root_id)
            if root_branch:
                summaries.append(
                    {
                        "root_id": root_id,
                        "name": root_branch.name,
                        "description": root_branch.description,
                        "branch_count": len(tree.branches),
                        "created_at": root_branch.created_at,
                    }
                )
        return summaries

    async def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch and all its descendants.

        Args:
            branch_id: The branch ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete root with children
        """
        root_id = self._branch_index.get(branch_id)
        if not root_id:
            return False

        tree = self._trees.get(root_id)
        if not tree:
            return False

        branch = tree.branches.get(branch_id)
        if not branch:
            return False

        # Find all descendants
        descendants = self._find_descendants(branch_id, tree)

        # Check if trying to delete root with other branches
        if branch_id == root_id and len(descendants) > 0:
            raise ValueError("Cannot delete root branch with existing children. " "Delete children first.")

        # Delete branch and descendants
        ids_to_delete = [branch_id] + descendants
        for bid in ids_to_delete:
            del tree.branches[bid]
            del self._branch_index[bid]
            # Delete from DB
            try:
                await self._repo.delete_branch(bid)
            except Exception as e:
                logger.warning(f"Failed to delete branch {bid} from DB: {e}")

        # If root was deleted and no branches remain, delete tree
        if branch_id == root_id:
            del self._trees[root_id]

        logger.info(f"Deleted branch {branch_id} and {len(descendants)} descendants")

        return True

    def _find_descendants(self, branch_id: str, tree: ScenarioTree) -> list[str]:
        """Find all descendant branch IDs."""
        descendants = []
        for bid, branch in tree.branches.items():
            if branch.parent_id == branch_id:
                descendants.append(bid)
                descendants.extend(self._find_descendants(bid, tree))
        return descendants
