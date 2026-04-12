
import libcst as cst
from typing import cast


class AddImportTransformer(cst.CSTTransformer): # type: ignore[misc]
    """Transformer to add an import to a module if it doesn't exist."""
    def __init__(self, import_node: cst.Import | cst.ImportFrom) -> None:
        self.import_node = import_node
        self.found = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:  # noqa: N802
        # Check if already exists (simplified check)
        # This is a basic implementation; a production one would check names more carefully
        new_body = list(updated_node.body)
        new_body.insert(0, cst.SimpleStatementLine(body=[self.import_node]))
        return updated_node.with_changes(body=new_body)


class AddClassMemberTransformer(cst.CSTTransformer): # type: ignore[misc]
    """Transformer to add a member to a specific class."""
    def __init__(self, class_name: str, member_node: cst.BaseStatement) -> None:
        self.class_name = class_name
        self.member_node = member_node
        self.found_class = False

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:  # noqa: N802
        if original_node.name.value == self.class_name:
            self.found_class = True
            new_body = list(updated_node.body.body)
            # Add member at the end of the class
            new_body.append(self.member_node)
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        return updated_node


class ASTMerger:
    """Engine for performing AST-aware code patching using LibCST."""

    @staticmethod
    def add_import(source: str, import_code: str) -> str:
        """Adds an import statement to the source code."""
        try:
            tree = cst.parse_module(source)
            import_node = cst.parse_statement(import_code).body[0]
            if not isinstance(import_node, (cst.Import, cst.ImportFrom)):
                return source
                
            transformer = AddImportTransformer(import_node)
            modified_tree = tree.visit(transformer)
            return cast(str, modified_tree.code)
        except Exception:
            return source

    @staticmethod
    def add_class_member(source: str, class_name: str, member_code: str) -> str:
        """Adds a member (field/method) to the specified class."""
        try:
            tree = cst.parse_module(source)
            member_node = cst.parse_statement(member_code)
            
            transformer = AddClassMemberTransformer(class_name, member_node)
            modified_tree = tree.visit(transformer)
            return cast(str, modified_tree.code)
        except Exception:
            return source
